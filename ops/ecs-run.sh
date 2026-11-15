#!/usr/bin/env bash
# Run a one-off command in the deployed API container, wait for it, and print its output.
#
#   ops/ecs-run.sh staging python -m app.cli create-superadmin --email you@example.com --name "You" --random-password
#   ops/ecs-run.sh staging python -m app.cli reset-mfa --email someone@example.com
#
# Needs AWS credentials for the account, and reads the cluster and network from Terraform outputs.
set -euo pipefail

env_name="${1:?usage: ecs-run.sh <staging|production> <command...>}"
shift
[ "$#" -gt 0 ] || { echo "usage: ecs-run.sh <staging|production> <command...>" >&2; exit 1; }

tf_dir="$(dirname "$0")/../infra/terraform/envs/${env_name}"
deploy="$(terraform -chdir="${tf_dir}" output -json deploy)"
cluster="$(jq -r .cluster_name <<<"${deploy}")"
family="$(jq -r .api_task_family <<<"${deploy}")"
subnets="$(jq -r '.task_network.subnets | join(",")' <<<"${deploy}")"
groups="$(jq -r '.task_network.security_groups | join(",")' <<<"${deploy}")"
command_json="$(jq -cn '$ARGS.positional' --args "$@")"

# Only the API container runs (the migrate container is skipped by overriding it to a no-op).
overrides="$(jq -cn --argjson cmd "${command_json}" \
  '{containerOverrides: [{name: "migrate", command: ["true"]}, {name: "api", command: $cmd}]}')"

task_arn="$(aws ecs run-task --cluster "${cluster}" --task-definition "${family}" \
  --launch-type FARGATE --count 1 --overrides "${overrides}" \
  --network-configuration "awsvpcConfiguration={subnets=[${subnets}],securityGroups=[${groups}],assignPublicIp=ENABLED}" \
  --query 'tasks[0].taskArn' --output text)"
echo "Started ${task_arn##*/}; waiting for it to finish…"
aws ecs wait tasks-stopped --cluster "${cluster}" --tasks "${task_arn}"

exit_code="$(aws ecs describe-tasks --cluster "${cluster}" --tasks "${task_arn}" \
  --query "tasks[0].containers[?name=='api'].exitCode | [0]" --output text)"
log_group="/${cluster}/api"
aws logs get-log-events --log-group-name "${log_group}" \
  --log-stream-name "api/api/${task_arn##*/}" --query 'events[].message' --output text || true
echo "Exit code: ${exit_code}"
[ "${exit_code}" = "0" ]
