"""Dreamworld: an original AI art series. Each episode is one invented, named place with its own short lore.
Everything here is fiction and every episode is labeled AI-generated."""
STYLE = "ultra detailed cinematic photograph, vivid colors, magical soft light, no people, no text, no watermark, vertical composition"
WORLDS = [
 ("Aeloria", "floating sky islands with long waterfalls pouring down into a sea of clouds, lush green grass and ancient trees",
  "The waterfalls here never reach the ground", "The islands drift a little every night", "Travelers follow the birds to find the way up"),
 ("Lumenwood", "a forest of giant softly glowing bioluminescent mushrooms with a winding mossy path and floating light specks",
  "The forest glows brighter when it rains", "Every mushroom hums a different note", "Paths light up under your footsteps"),
 ("Glassmere", "a perfectly clear lake like liquid glass over glowing colorful stones, snowy mountains around it",
  "The water is so clear boats seem to fly", "The stones glow at night like stars", "Nobody has ever found the bottom"),
 ("Sakura Hollow", "a quiet valley of enormous ancient cherry blossom trees, pink petals in the air, a small stone bridge over a stream",
  "These trees have bloomed for a thousand years", "The petals never touch the ground", "The stream flows pink in spring"),
 ("The Cloud Steps", "an endless stone staircase rising from a flower meadow into golden clouds at sunrise",
  "No one knows who built the steps", "Each step is warm, even in winter", "At the top, the clouds feel like cotton"),
 ("Emberdune", "glowing amber crystal sand dunes in a desert at blue hour with a giant moon on the horizon",
  "The dunes glow for hours after sunset", "The sand sings when the wind blows", "Two moons rise here every night"),
 ("Frostveil", "a city of glowing ice caves with warm golden lanterns, blue translucent ice walls and frozen waterfalls",
  "The ice here is warm to the touch", "Lanterns never melt the walls", "Snow falls upward at midnight"),
 ("Velvet Isles", "tiny round islands covered in soft green moss floating on calm turquoise water, gentle morning mist",
  "The moss feels like velvet", "The islands slowly rotate with the tide", "Whales sleep beneath them"),
 ("Starfall Lake", "a mountain lake that perfectly reflects a vivid galaxy sky, glowing paper lanterns floating on the water",
  "The lake reflects stars even in daylight", "Every lantern carries a wish", "Shooting stars fall into the water"),
 ("Lantern Canopy", "a treehouse village high in giant ancient trees connected by rope bridges, warm lanterns at dusk",
  "The village was built without a single nail", "Lanterns light themselves at sunset", "The trees grow a new room every year"),
 ("Amberleaf Vale", "an autumn valley of golden trees with a glowing river winding through it, falling leaves in warm light",
  "It is always autumn here", "The river glows like melted honey", "Leaves fall but the trees never go bare"),
 ("Coral Sky", "a giant pink and orange coral reef floating in the sky above the clouds, with fish swimming through the air",
  "Fish here swim through the air", "The reef floats higher every year", "At sunset the whole sky turns coral"),
 ("Mirror Peaks", "jagged mountains reflected in a vast salt mirror at sunset, two moons in a pastel sky",
  "The mirror never cracks or melts", "Walk far enough and you see the sky below", "Two moons light the salt at night"),
 ("Bloomreach", "an endless valley of giant glowing blue flowers taller than trees beside a calm river",
  "The flowers open only at night", "Their glow guides lost travelers home", "Each flower is taller than a house"),
 ("Aurora Terraces", "glowing rice terraces on a mountain under a vivid green and purple aurora sky",
  "The terraces glow under the aurora", "Water here flows uphill", "The aurora sings on quiet nights"),
 ("Moonwell Falls", "a waterfall made of glowing silver light falling into a moonlit pool in a mossy canyon",
  "The falls only flow under a full moon", "The water tastes like rain", "Its pool reflects your dreams"),
 ("Pearlshore", "a beach of pearl white sand with soft lavender waves and pastel sky, smooth glowing shells",
  "The waves here are lavender", "Shells glow softly at dusk", "The sand is always cool and soft"),
 ("Driftwood Harbor", "old wooden sailing boats floating among soft pink clouds above a sleeping sea, warm sunset light",
  "Boats here sail on clouds", "The harbor moves with the wind", "Sailors say it appears only at sunset"),
]
SHOTS = ["wide aerial establishing shot", "eye level view along a path", "close-up of small magical details", "at sunrise",
         "at night, softly glowing", "seen from above", "reflection in still water", "with soft mist", "low angle looking up",
         "panoramic view", "golden hour light", "blue hour glow", "dreamy close detail with shallow depth of field"]
def episode(n):
    name, base, *lore = WORLDS[n % len(WORLDS)]
    prompts = [f"{base}, {s}, {STYLE}" for s in SHOTS]
    return name, prompts, lore
