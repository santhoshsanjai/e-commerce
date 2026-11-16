"""The sample catalogue: 5 categories, 5 brands and 50 products.

Prices are in pounds sterling (whole pence). Brands are fictional.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SampleCategory:
    slug: str
    name: str
    backdrop: str  # picture background colour


@dataclass(frozen=True)
class SampleProduct:
    name: str
    category: str  # SampleCategory.slug
    brand: str
    kind: str  # drawing in app.seed.images
    color: str
    accent: str
    price: int  # pence
    stock: int
    short: str
    description: str
    compare_at: int | None = None
    attributes: dict[str, str] = field(default_factory=dict)


CATEGORIES = [
    SampleCategory("home-living", "Home & Living", "#ece8e1"),
    SampleCategory("kitchen-dining", "Kitchen & Dining", "#e9ece8"),
    SampleCategory("bags-accessories", "Bags & Accessories", "#ebe7e4"),
    SampleCategory("stationery-desk", "Stationery & Desk", "#e7eaee"),
    SampleCategory("audio-tech", "Audio & Tech", "#e6e8ec"),
]

BRANDS = ["Marlowe Home", "Albury Kitchen", "Harrow & Finch", "Thames Paper Co.", "Kestrel Audio"]

NAVY = "#1f3a5f"
GOLD = "#c9a227"

PRODUCTS = [
    # ---------- Home & Living ----------
    SampleProduct(
        "Fig & Cedar Soy Candle",
        "home-living",
        "Marlowe Home",
        "candle",
        "#2b3a4a",
        "#9a7b4f",
        2800,
        64,
        "Hand-poured soy wax with notes of ripe fig, cedarwood and a hint of black pepper.",
        "Poured by hand in small batches in Sussex, this candle pairs ripe fig with warm cedarwood "
        "for a scent that fills a living room without overpowering it. The cotton wick burns "
        "cleanly and evenly, and the matte tin can be reused once the candle is finished.",
        attributes={"Burn time": "Approx. 45 hours", "Wax": "100% soy", "Weight": "220 g"},
    ),
    SampleProduct(
        "Linen Blend Cushion, Ink Navy",
        "home-living",
        "Marlowe Home",
        "cushion",
        NAVY,
        GOLD,
        3500,
        42,
        "A relaxed linen and cotton cover with a feather-filled inner, in deep ink navy.",
        "Woven from a soft linen and cotton blend that gets better with every wash, this cushion "
        "brings quiet colour to a sofa or armchair. It comes with a plump duck-feather inner and "
        "a concealed zip, so the cover is easy to take off and launder.",
        attributes={
            "Size": "50 x 50 cm",
            "Cover": "55% linen, 45% cotton",
            "Filling": "Duck feather",
        },
    ),
    SampleProduct(
        "Merino Herringbone Throw",
        "home-living",
        "Marlowe Home",
        "throw",
        "#6b7a8f",
        "#c7b9a5",
        8900,
        18,
        "A generous merino wool throw in a classic herringbone weave with fringed edges.",
        "Woven in a Yorkshire mill from fine merino wool, this throw is warm without being heavy. "
        "The herringbone pattern and finished fringe make it as handsome folded at the end of a "
        "bed as it is draped over a reading chair.",
        compare_at=11000,
        attributes={"Size": "130 x 180 cm", "Material": "100% merino wool", "Care": "Dry clean"},
    ),
    SampleProduct(
        "Stoneware Bud Vase, Sage",
        "home-living",
        "Marlowe Home",
        "vase",
        "#8a9a85",
        "#d9b25f",
        2200,
        55,
        "A small reactive-glaze vase for a single stem or a few dried flowers.",
        "Thrown and glazed by hand, every vase has its own subtle variation in colour. The narrow "
        "neck holds one or two stems upright, making it ideal for a windowsill, mantelpiece or "
        "bedside table.",
        attributes={"Height": "18 cm", "Material": "Stoneware", "Watertight": "Yes"},
    ),
    SampleProduct(
        "Wild Rhubarb Reed Diffuser",
        "home-living",
        "Marlowe Home",
        "diffuser",
        "#c48b8b",
        "#5b4636",
        3200,
        37,
        "Sharp rhubarb softened with vanilla and musk, released through natural rattan reeds.",
        "A bright, fresh fragrance for a hallway or bathroom that lasts for months. Turn the reeds "
        "once a week to refresh the scent. Presented in a weighted glass bottle that looks "
        "smart on any shelf.",
        attributes={"Volume": "200 ml", "Lasts": "Up to 12 weeks", "Reeds": "8 rattan"},
    ),
    SampleProduct(
        "Oatmeal Bouclé Cushion",
        "home-living",
        "Marlowe Home",
        "cushion",
        "#d8cdbd",
        "#8c7356",
        3900,
        26,
        "A tactile bouclé cushion in warm oatmeal with a contrast walnut button.",
        "Bouclé's looped texture adds instant depth to a neutral scheme. This cushion is finished "
        "with a single covered button and a feather inner for a full, generous shape.",
        attributes={"Size": "45 x 45 cm", "Cover": "Polyester bouclé", "Filling": "Duck feather"},
    ),
    SampleProduct(
        "Amber & Oud Candle, Large",
        "home-living",
        "Marlowe Home",
        "candle",
        "#5a3e2b",
        "#c9a227",
        4500,
        3,
        "A rich, evening fragrance of amber, oud and smoked vanilla in a three-wick tin.",
        "Designed for larger rooms, this three-wick candle builds a warm, enveloping scent within "
        "minutes. Trim the wicks to 5 mm before each burn for a clean, steady flame.",
        attributes={"Burn time": "Approx. 70 hours", "Wax": "Soy and coconut", "Weight": "450 g"},
    ),
    SampleProduct(
        "Ribbed Ceramic Vase, Chalk",
        "home-living",
        "Marlowe Home",
        "vase",
        "#eae6df",
        "#8a9a85",
        3400,
        21,
        "A tall ribbed vase in a soft chalk-white matte finish.",
        "Fine vertical ribs catch the light and give this vase a sculptural presence even when it "
        "is empty. Wide enough at the base for a generous bunch of eucalyptus or garden roses.",
        attributes={"Height": "28 cm", "Material": "Ceramic", "Finish": "Matte"},
    ),
    SampleProduct(
        "Cashmere Blend Throw, Charcoal",
        "home-living",
        "Marlowe Home",
        "throw",
        "#3d4148",
        "#8d8f94",
        12500,
        9,
        "An exceptionally soft wool and cashmere throw in deep charcoal.",
        "A blend of lambswool and cashmere gives this throw a lightweight, cloud-soft handle. "
        "Finished with a neat whipstitched edge, it makes a lasting gift.",
        attributes={"Size": "140 x 190 cm", "Material": "85% lambswool, 15% cashmere"},
    ),
    SampleProduct(
        "English Garden Reed Diffuser",
        "home-living",
        "Marlowe Home",
        "diffuser",
        "#9fb59b",
        "#4f5f4c",
        3200,
        48,
        "Green tomato leaf, sweet pea and cut grass, inspired by a walled kitchen garden.",
        "A fresh, green scent that brings the feel of a summer garden indoors all year round. "
        "Alcohol-free formula in a recyclable glass bottle.",
        attributes={"Volume": "200 ml", "Lasts": "Up to 12 weeks", "Reeds": "8 rattan"},
    ),
    # ---------- Kitchen & Dining ----------
    SampleProduct(
        "Glazed Stoneware Mug, Navy",
        "kitchen-dining",
        "Albury Kitchen",
        "mug",
        NAVY,
        GOLD,
        1400,
        120,
        "A generous everyday mug with a deep navy glaze and a comfortable handle.",
        "Made from durable stoneware that keeps tea hot for longer. The reactive glaze pools "
        "slightly differently on every mug, so no two are quite the same.",
        attributes={"Capacity": "350 ml", "Dishwasher safe": "Yes", "Microwave safe": "Yes"},
    ),
    SampleProduct(
        "Speckled Breakfast Bowl",
        "kitchen-dining",
        "Albury Kitchen",
        "bowl",
        "#e6dfd3",
        "#7d6a55",
        1600,
        84,
        "A wide stoneware bowl in a speckled cream glaze for cereals, soups and salads.",
        "Shaped with a gently flared rim, this bowl is roomy enough for a hearty breakfast or a "
        "bowl of ramen. Stacks neatly with the rest of the speckled collection.",
        attributes={"Diameter": "17 cm", "Dishwasher safe": "Yes"},
    ),
    SampleProduct(
        "Dinner Plate Set of 4, Slate",
        "kitchen-dining",
        "Albury Kitchen",
        "plates",
        "#5f6b78",
        "#c9cfd6",
        5200,
        30,
        "Four rimmed stoneware dinner plates in a cool slate-blue glaze.",
        "These plates bring a calm, contemporary feel to the table. Fired at high temperature for "
        "strength and chip resistance, they move happily from oven to table to dishwasher.",
        compare_at=6400,
        attributes={"Diameter": "27 cm", "Set of": "4", "Oven safe": "Up to 200°C"},
    ),
    SampleProduct(
        "Hand-blown Glass Carafe",
        "kitchen-dining",
        "Albury Kitchen",
        "carafe",
        "#7c96a8",
        "#2c3e50",
        2900,
        40,
        "A hand-blown carafe for water or wine, with a fitted glass stopper.",
        "Light, clear and pleasingly thin, this carafe is blown by hand from borosilicate glass so "
        "it can also take chilled or warm drinks. A timeless piece for the dinner table.",
        attributes={"Capacity": "1 litre", "Material": "Borosilicate glass"},
    ),
    SampleProduct(
        "Insulated Steel Bottle, 750 ml",
        "kitchen-dining",
        "Albury Kitchen",
        "bottle",
        "#2f4f4f",
        "#b9a06a",
        3000,
        95,
        "Double-walled stainless steel that keeps drinks cold for 24 hours or hot for 12.",
        "A leak-proof bottle built for the commute, the gym and the office. The powder-coated "
        "finish resists scratches and the loop lid makes it easy to carry.",
        attributes={"Capacity": "750 ml", "Cold": "24 hours", "Hot": "12 hours", "BPA free": "Yes"},
    ),
    SampleProduct(
        "Travel Tumbler with Straw",
        "kitchen-dining",
        "Albury Kitchen",
        "tumbler",
        "#c9b8a6",
        "#4a3b2f",
        2400,
        66,
        "An insulated tumbler with a sliding lid and reusable steel straw.",
        "Fits most car cup holders and keeps iced coffee cold all afternoon. The tapered shape "
        "is comfortable to hold and the lid seals with a quarter turn.",
        attributes={
            "Capacity": "500 ml",
            "Material": "Stainless steel",
            "Dishwasher safe": "Lid only",
        },
    ),
    SampleProduct(
        "Recycled Glass Tumblers, Set of 2",
        "kitchen-dining",
        "Albury Kitchen",
        "glasses",
        "#8fa6a0",
        "#d6c690",
        1800,
        70,
        "Two chunky tumblers made from 100% recycled glass with a subtle green tint.",
        "Each tumbler is pressed from recycled glass, so small bubbles and slight colour "
        "variations are part of its character. Perfect for water, juice or a gin and tonic.",
        attributes={"Capacity": "300 ml each", "Set of": "2", "Material": "Recycled glass"},
    ),
    SampleProduct(
        "Stoneware Mug, Chalk White",
        "kitchen-dining",
        "Albury Kitchen",
        "mug",
        "#eeebe5",
        "#8a9a85",
        1400,
        0,
        "Our classic everyday mug in a soft chalk-white glaze.",
        "The same comfortable shape as our best-selling navy mug, finished in a clean matte white "
        "that suits any kitchen. Back in stock soon.",
        attributes={"Capacity": "350 ml", "Dishwasher safe": "Yes", "Microwave safe": "Yes"},
    ),
    SampleProduct(
        "Serving Bowl, Midnight Glaze",
        "kitchen-dining",
        "Albury Kitchen",
        "bowl",
        "#24324a",
        "#c9a227",
        3200,
        22,
        "A large serving bowl with a glossy midnight glaze and a contrasting raw rim.",
        "Sized for salads, pasta and Sunday roasts, this bowl takes centre stage on the table. "
        "Pair it with our slate dinner plates for a coordinated look.",
        attributes={"Diameter": "28 cm", "Dishwasher safe": "Yes"},
    ),
    SampleProduct(
        "Side Plate Set of 4, Oat",
        "kitchen-dining",
        "Albury Kitchen",
        "plates",
        "#d9ccb6",
        "#8c7356",
        3600,
        4,
        "Four speckled side plates for toast, cake and small plates.",
        "A versatile size for everything from breakfast to dessert. Finished in our warm oat "
        "glaze with a fine dark speckle.",
        attributes={"Diameter": "21 cm", "Set of": "4", "Dishwasher safe": "Yes"},
    ),
    # ---------- Bags & Accessories ----------
    SampleProduct(
        "Waxed Canvas Tote, Navy",
        "bags-accessories",
        "Harrow & Finch",
        "tote",
        NAVY,
        "#a8763e",
        6500,
        34,
        "A roomy waxed cotton tote with leather handles and an inner zip pocket.",
        "Cut from weather-resistant waxed canvas that develops a lived-in patina over time. "
        "Fits a 15-inch laptop, and the vegetable-tanned leather handles are reinforced with "
        "copper rivets.",
        attributes={
            "Size": "40 x 36 x 14 cm",
            "Material": "Waxed cotton, leather",
            "Laptop": "Up to 15 in",
        },
    ),
    SampleProduct(
        "Leather Bifold Wallet, Tan",
        "bags-accessories",
        "Harrow & Finch",
        "wallet",
        "#a8763e",
        GOLD,
        5500,
        46,
        "A slim bifold wallet in full-grain leather with six card slots.",
        "Crafted from full-grain leather tanned in Northamptonshire, this wallet softens and "
        "darkens beautifully with use. Slim enough for a jacket pocket, with space for notes "
        "and receipts.",
        attributes={"Card slots": "6", "Material": "Full-grain leather", "Size": "11 x 9 cm"},
    ),
    SampleProduct(
        "Everyday Backpack, Charcoal",
        "bags-accessories",
        "Harrow & Finch",
        "backpack",
        "#3d4148",
        "#a8763e",
        9500,
        27,
        "A clean-lined backpack with a padded laptop sleeve and water-resistant base.",
        "Designed for city commutes, with a quick-access front pocket, a padded 16-inch laptop "
        "sleeve and breathable back panel. Made from recycled polyester with a durable coating.",
        compare_at=12000,
        attributes={
            "Capacity": "20 litres",
            "Laptop": "Up to 16 in",
            "Material": "Recycled polyester",
        },
    ),
    SampleProduct(
        "Weekend Holdall, Olive",
        "bags-accessories",
        "Harrow & Finch",
        "duffel",
        "#5d6448",
        "#a8763e",
        14500,
        12,
        "A structured canvas holdall with leather trims, sized for cabin luggage.",
        "Everything you need for a weekend away, in one smart bag. Twin grab handles, a "
        "detachable shoulder strap and a separate shoe compartment keep things organised.",
        attributes={"Capacity": "40 litres", "Size": "52 x 30 x 28 cm", "Cabin size": "Yes"},
    ),
    SampleProduct(
        "Leather Card Holder, Navy",
        "bags-accessories",
        "Harrow & Finch",
        "card_holder",
        NAVY,
        "#e0d7c6",
        2500,
        88,
        "A minimal four-slot card holder in smooth navy leather.",
        "Holds your everyday cards and a folded note without adding bulk. Hand-finished edges "
        "and a centre pocket make it a thoughtful gift.",
        attributes={"Card slots": "4 plus centre pocket", "Material": "Calf leather"},
    ),
    SampleProduct(
        "Classic Field Watch, Navy Strap",
        "bags-accessories",
        "Harrow & Finch",
        "watch",
        NAVY,
        GOLD,
        18500,
        15,
        "A 38 mm field watch with a cream dial, sapphire crystal and navy leather strap.",
        "A refined everyday watch with clear, legible numerals and a Japanese quartz movement. "
        "The brushed steel case is water resistant to 50 metres and the strap changes without "
        "tools.",
        attributes={
            "Case": "38 mm stainless steel",
            "Movement": "Japanese quartz",
            "Water resistance": "5 ATM",
        },
    ),
    SampleProduct(
        "Canvas Market Tote, Natural",
        "bags-accessories",
        "Harrow & Finch",
        "tote",
        "#d8cdb5",
        "#2b3a4a",
        2800,
        110,
        "A sturdy organic cotton tote for shopping trips and days out.",
        "Heavyweight organic cotton canvas with long handles that sit comfortably on the "
        "shoulder. Folds flat to keep in a bag for unplanned shopping.",
        attributes={"Size": "42 x 38 cm", "Material": "Organic cotton canvas"},
    ),
    SampleProduct(
        "Zip Wallet, Burgundy",
        "bags-accessories",
        "Harrow & Finch",
        "wallet",
        "#6d2b33",
        "#d9b25f",
        6500,
        2,
        "A zip-around leather wallet with a coin pocket and eight card slots.",
        "Rich burgundy leather and a smooth brass zip combine in a wallet that keeps everything "
        "secure. A popular choice, with limited stock remaining.",
        attributes={"Card slots": "8", "Material": "Full-grain leather", "Hardware": "Brass"},
    ),
    SampleProduct(
        "Roll-top Backpack, Navy",
        "bags-accessories",
        "Harrow & Finch",
        "backpack",
        "#263b57",
        "#d9b25f",
        11000,
        19,
        "A waterproof roll-top backpack that expands from 18 to 24 litres.",
        "Built for unpredictable British weather, with welded seams and a roll-top closure that "
        "keeps the rain out. A side zip gives quick access to the main compartment.",
        attributes={"Capacity": "18 to 24 litres", "Waterproof": "Yes", "Laptop": "Up to 15 in"},
    ),
    SampleProduct(
        "Automatic Dress Watch, Black",
        "bags-accessories",
        "Harrow & Finch",
        "watch",
        "#1d1f24",
        "#d4d4d4",
        32000,
        6,
        "A 40 mm automatic watch with a silver dial and black alligator-grain strap.",
        "A self-winding movement with a 40-hour power reserve, visible through the exhibition "
        "case back. Understated enough for every day, polished enough for black tie.",
        attributes={
            "Case": "40 mm stainless steel",
            "Movement": "Automatic",
            "Power reserve": "40 hours",
        },
    ),
    # ---------- Stationery & Desk ----------
    SampleProduct(
        "A5 Linen Notebook, Navy",
        "stationery-desk",
        "Thames Paper Co.",
        "notebook",
        NAVY,
        GOLD,
        1800,
        140,
        "A lay-flat linen-bound notebook with 192 pages of dot-grid paper.",
        "Bound in book cloth with an elastic closure and ribbon marker. The 100 gsm paper is "
        "smooth enough for fountain pens and resists bleed-through.",
        attributes={"Size": "A5", "Pages": "192", "Paper": "100 gsm dot grid"},
    ),
    SampleProduct(
        "A5 Linen Notebook, Sage",
        "stationery-desk",
        "Thames Paper Co.",
        "notebook",
        "#8a9a85",
        "#3d4a3a",
        1800,
        96,
        "Our lay-flat dot-grid notebook in a soft sage book cloth.",
        "The same lay-flat binding and 100 gsm paper as the rest of the collection, in a calm "
        "green that brightens a desk.",
        attributes={"Size": "A5", "Pages": "192", "Paper": "100 gsm dot grid"},
    ),
    SampleProduct(
        "Brass Rollerball Pen",
        "stationery-desk",
        "Thames Paper Co.",
        "pen",
        "#b08d57",
        "#3a3226",
        3800,
        52,
        "A solid brass rollerball that develops a warm patina with use.",
        "Machined from a single bar of brass and weighted for a balanced, comfortable grip. "
        "Takes standard rollerball refills and arrives with a black ink cartridge.",
        attributes={
            "Material": "Solid brass",
            "Refill": "Standard rollerball",
            "Length": "13.5 cm",
        },
    ),
    SampleProduct(
        "Lacquered Fountain Pen, Navy",
        "stationery-desk",
        "Thames Paper Co.",
        "pen",
        NAVY,
        GOLD,
        6500,
        24,
        "A lacquered fountain pen with a gold-plated steel medium nib.",
        "Deep navy lacquer and gold-plated trims make this pen a pleasure to write with and to "
        "give. Fills from cartridges or the supplied converter.",
        compare_at=7800,
        attributes={"Nib": "Medium, gold-plated steel", "Filling": "Cartridge or converter"},
    ),
    SampleProduct(
        "Oak Desk Organiser",
        "stationery-desk",
        "Thames Paper Co.",
        "desk_tray",
        "#b48a5a",
        "#2b3a4a",
        4500,
        31,
        "A solid oak organiser with three compartments for pens, cards and clips.",
        "Made from FSC-certified oak and finished with natural oil. A simple way to bring order "
        "to a busy desk.",
        attributes={"Size": "30 x 12 x 6 cm", "Material": "Solid oak", "Finish": "Natural oil"},
    ),
    SampleProduct(
        "Pocket Notebook Trio, Kraft",
        "stationery-desk",
        "Thames Paper Co.",
        "notebook",
        "#b9976b",
        "#2b3a4a",
        1200,
        160,
        "Three stapled pocket notebooks with plain, lined and squared pages.",
        "Small enough for a back pocket and sturdy enough for daily notes, lists and sketches. "
        "Printed in London on recycled paper.",
        attributes={"Size": "9 x 14 cm", "Set of": "3", "Paper": "Recycled"},
    ),
    SampleProduct(
        "Walnut Pen Tray",
        "stationery-desk",
        "Thames Paper Co.",
        "desk_tray",
        "#5c3f2b",
        GOLD,
        3500,
        0,
        "A walnut tray with two compartments to keep pens and paper clips at hand.",
        "Turned from American black walnut with softly rounded edges. Back in stock soon.",
        attributes={"Size": "24 x 9 x 3 cm", "Material": "American walnut"},
    ),
    SampleProduct(
        "Leather Journal, Tan",
        "stationery-desk",
        "Thames Paper Co.",
        "notebook",
        "#a8763e",
        "#5c3f2b",
        4200,
        28,
        "A refillable leather journal cover with a lined A5 insert.",
        "Full-grain leather wraps a replaceable notebook insert, so the cover lasts for years. "
        "Embossing is available on request.",
        attributes={"Size": "A5", "Material": "Full-grain leather", "Insert": "Lined, refillable"},
    ),
    SampleProduct(
        "Aluminium Ballpoint, Graphite",
        "stationery-desk",
        "Thames Paper Co.",
        "pen",
        "#4a4f57",
        "#c0c4ca",
        2200,
        75,
        "A lightweight anodised aluminium ballpoint with a twist mechanism.",
        "Precision-made and pleasingly light, with a smooth twist action and a long-lasting "
        "black refill.",
        attributes={"Material": "Anodised aluminium", "Refill": "Standard ballpoint"},
    ),
    SampleProduct(
        "Weekly Desk Planner",
        "stationery-desk",
        "Thames Paper Co.",
        "notebook",
        "#d9ccb6",
        NAVY,
        1600,
        60,
        "An undated weekly planner pad with 52 tear-off sheets.",
        "Plan the week at a glance, with space for priorities and notes. Undated, so you can "
        "start any time of year.",
        attributes={"Size": "A4 landscape", "Sheets": "52", "Dated": "No"},
    ),
    # ---------- Audio & Tech ----------
    SampleProduct(
        "Wireless Over-ear Headphones",
        "audio-tech",
        "Kestrel Audio",
        "headphones",
        "#2b2f36",
        GOLD,
        19900,
        23,
        "Active noise cancelling headphones with 35-hour battery life and plush ear cushions.",
        "Tuned for a rich, balanced sound and finished in soft-touch materials. Adaptive noise "
        "cancelling quietens trains and open-plan offices, and a five-minute charge gives two "
        "hours of listening.",
        compare_at=24900,
        attributes={"Battery": "Up to 35 hours", "Noise cancelling": "Active", "Bluetooth": "5.3"},
    ),
    SampleProduct(
        "Wireless Headphones, Stone",
        "audio-tech",
        "Kestrel Audio",
        "headphones",
        "#d6cfc4",
        "#8c7356",
        19900,
        14,
        "Our noise cancelling over-ear headphones in a warm stone colourway.",
        "All the comfort and sound of our flagship headphones, in a light, natural finish. "
        "Folds flat into the supplied travel case.",
        attributes={"Battery": "Up to 35 hours", "Noise cancelling": "Active", "Bluetooth": "5.3"},
    ),
    SampleProduct(
        "Portable Bluetooth Speaker",
        "audio-tech",
        "Kestrel Audio",
        "speaker",
        NAVY,
        GOLD,
        8900,
        38,
        "A compact speaker with room-filling sound and 16 hours of playback.",
        "Wrapped in a recycled fabric grille and rated IP67 against dust and water, so it is as "
        "at home in the garden as it is on a bookshelf. Pair two for stereo sound.",
        attributes={"Battery": "Up to 16 hours", "Water resistance": "IP67", "Bluetooth": "5.3"},
    ),
    SampleProduct(
        "Home Speaker, Charcoal",
        "audio-tech",
        "Kestrel Audio",
        "speaker",
        "#3d4148",
        "#c0c4ca",
        14900,
        11,
        "A Wi-Fi and Bluetooth speaker with deep bass for living rooms.",
        "Stream from your favourite apps over Wi-Fi or connect any device via Bluetooth. Two "
        "woofers and a tweeter deliver clear vocals and deep, controlled bass.",
        attributes={"Connectivity": "Wi-Fi, Bluetooth 5.3", "Drivers": "2 woofers, 1 tweeter"},
    ),
    SampleProduct(
        "True Wireless Earbuds",
        "audio-tech",
        "Kestrel Audio",
        "earbuds",
        "#eeebe5",
        NAVY,
        12900,
        45,
        "Compact earbuds with noise cancelling and a pocket-sized charging case.",
        "Three sizes of ear tip help you find a secure, comfortable fit. Up to eight hours of "
        "listening per charge, with a further 24 hours from the case.",
        attributes={
            "Battery": "8 hours, 32 with case",
            "Noise cancelling": "Active",
            "Water resistance": "IPX4",
        },
    ),
    SampleProduct(
        "True Wireless Earbuds, Midnight",
        "audio-tech",
        "Kestrel Audio",
        "earbuds",
        "#1f2937",
        GOLD,
        12900,
        5,
        "Our noise cancelling earbuds in a matte midnight finish.",
        "The same sound and battery life as the original, in a discreet dark colour. Supports "
        "wireless charging.",
        attributes={
            "Battery": "8 hours, 32 with case",
            "Noise cancelling": "Active",
            "Water resistance": "IPX4",
        },
    ),
    SampleProduct(
        "Wireless Charging Pad",
        "audio-tech",
        "Kestrel Audio",
        "charger",
        "#2b3a4a",
        "#c0c4ca",
        3500,
        82,
        "A slim 15 W wireless charger wrapped in soft fabric.",
        "Charges compatible phones and earbuds through most cases. The non-slip base keeps it "
        "in place on a desk or bedside table, and a USB-C cable is included.",
        attributes={"Output": "Up to 15 W", "Cable": "USB-C, 1.5 m included"},
    ),
    SampleProduct(
        "Wireless Charging Pad, Oat",
        "audio-tech",
        "Kestrel Audio",
        "charger",
        "#d9ccb6",
        "#8c7356",
        3500,
        57,
        "Our slim 15 W wireless charger in a warm oat fabric.",
        "Designed to blend into the home rather than stand out. Includes a braided USB-C cable.",
        compare_at=4200,
        attributes={"Output": "Up to 15 W", "Cable": "USB-C, 1.5 m included"},
    ),
    SampleProduct(
        "Mini Speaker, Sage",
        "audio-tech",
        "Kestrel Audio",
        "speaker",
        "#8a9a85",
        "#3d4a3a",
        5900,
        33,
        "A palm-sized waterproof speaker with a carry loop.",
        "Small enough to pack for a picnic and loud enough to fill a kitchen. Up to 12 hours of "
        "playback from a single charge.",
        attributes={"Battery": "Up to 12 hours", "Water resistance": "IP67", "Weight": "290 g"},
    ),
    SampleProduct(
        "Studio Headphones, Navy",
        "audio-tech",
        "Kestrel Audio",
        "headphones",
        NAVY,
        "#c0c4ca",
        14900,
        20,
        "Closed-back wired headphones tuned for accurate, detailed listening.",
        "A favourite with musicians and podcasters, these headphones pair a neutral sound with "
        "memory-foam cushions for long sessions. Includes a detachable coiled cable and a "
        "6.35 mm adaptor.",
        attributes={"Type": "Closed-back, wired", "Driver": "45 mm", "Cable": "Detachable, 3 m"},
    ),
]
