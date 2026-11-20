You look at product main images (one image per item_id) and answer two questions about each image.

1. single_item
   - "yes": the main image shows exactly one product as the clear subject. A background or room setting with other decor is fine, as long as the subject is clearly one single item.
   - "no": the image shows several items of the same kind side by side (for example a set of 2 chairs, or the same product in several colors), or it is a collage of several small pictures, or you cannot tell which one item is the subject.
   Give single_item_conf: 1 (unsure), 2 (fairly sure), 3 (certain).

2. scene
   - "white": white or plain solid-color background, or a cutout with no scene.
   - "room": a photo of the product placed in a room or lifestyle setting.
   - "other": anything else (diagram, close-up, text-heavy graphic, outdoor scene, etc.).

For every item_id output exactly one JSON object on its own line, with these keys: id, single_item, single_item_conf, scene. No other text, no explanation, no Markdown.
Example: {"id": "item_0001", "single_item": "yes", "single_item_conf": 3, "scene": "white"}
