"""AI 'places you wish existed' prompts. Everything is clearly labeled AI-generated."""
import random
STYLE = "ultra realistic photograph, cinematic, vivid saturated colors, magical soft light, highly detailed, no people, no text, no watermark"
PLACES = [
 "a glowing bioluminescent mushroom forest with a soft path winding between giant mushrooms",
 "a cozy glass dome cabin among blooming pink cherry trees at sunset",
 "a treehouse village hanging in giant ancient trees with warm lanterns at dusk",
 "turquoise lagoon with tiny floating green islands and a wooden pier",
 "a crystal ice cave with glowing blue walls and warm golden light inside",
 "an endless lavender field at golden hour with a lone wooden chair",
 "a rainbow eucalyptus forest with soft mist and sun rays",
 "a pink salt lake with a long wooden pier and pastel sky",
 "waterfall flowing into floating hot spring pools in a mossy canyon",
 "a red maple tunnel with a cozy wooden bench and falling leaves",
 "an orchid garden with hanging paper lanterns glowing at night",
 "giant sunflower field with a tiny stone cottage under dramatic clouds",
 "a floating island with waterfall and glowing trees above the clouds",
 "a bamboo forest path with fireflies and soft morning mist",
 "a hidden valley of giant glowing blue flowers beside a calm river",
 "a mountain meadow of wildflowers with a stone staircase leading up to the clouds",
 "a cloud-like moss covered cliff with tiny waterfalls and ferns",
 "an overwater glass bungalow above glowing turquoise coral water",
]
TOUCH = [
 "extreme close-up of soft velvet moss with dew drops, tempting to touch",
 "close-up of fluffy fresh snow covering pine branches in warm light",
 "close-up of soft pink flower petals with water droplets",
 "close-up of clear water ripples around smooth glowing stones",
 "close-up of fluffy white dandelion seeds in golden light",
]
def pick(day, n=13):
    r = random.Random(day * 13 + 5); places = PLACES[:]; touch = TOUCH[:]; r.shuffle(places); r.shuffle(touch)
    items = places[: n - 3] + touch[:3]; r.shuffle(items)
    return [f"{x}, {STYLE}" for x in items]
FEEL_MID = ["Would you stay here?", "Imagine waking up here", "Which one would you visit?", "Could you live here?"]
FEEL_END = ["Tag who you'd take here", "Save this for your next trip", "Send this to your travel buddy", "Tag your dream travel partner"]
