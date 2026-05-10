

from __future__ import annotations

import json

from endstone.nbt import (
    CompoundTag, ListTag, ByteTag, ShortTag, IntTag, LongTag,
    FloatTag, DoubleTag, StringTag, ByteArrayTag, IntArrayTag,
)


class ItemSerializer:




    def serialize(self, type_id: str, amount: int, data: int = 0, nbt: CompoundTag | None = None) -> str:

        payload: dict = {
            "type": type_id,
            "amount": amount,
            "data": data,
        }
        if nbt is not None and len(nbt) > 0:
            payload["nbt"] = self._tag_to_json(nbt)
        return json.dumps(payload)



    def deserialize(self, data_json: str) -> dict:

        try:
            parsed = json.loads(data_json)
        except json.JSONDecodeError:
            return {"type": "minecraft:air", "amount": 1, "data": 0, "nbt": None}

        result: dict = {
            "type": parsed.get("type", "minecraft:air"),
            "amount": parsed.get("amount", 1),
            "data": parsed.get("data", 0),
            "nbt": None,
        }

        nbt_data = parsed.get("nbt")
        if nbt_data is not None:
            try:
                result["nbt"] = self._json_to_tag(nbt_data)
            except Exception:
                result["nbt"] = None

        return result



    def get_display_name(self, type_id: str) -> str:

        if ":" in type_id:
            type_id = type_id.split(":", 1)[1]
        words = type_id.split("_")
        return " ".join(word.capitalize() for word in words)



    def _tag_to_json(self, tag) -> dict:

        if isinstance(tag, CompoundTag):
            return {"_t": "compound", "_v": {k: self._tag_to_json(v) for k, v in tag.items()}}
        if isinstance(tag, ListTag):
            return {"_t": "list", "_v": [self._tag_to_json(v) for v in tag]}
        if isinstance(tag, ByteTag):
            return {"_t": "byte", "_v": tag.value}
        if isinstance(tag, ShortTag):
            return {"_t": "short", "_v": tag.value}
        if isinstance(tag, IntTag):
            return {"_t": "int", "_v": tag.value}
        if isinstance(tag, LongTag):
            return {"_t": "long", "_v": tag.value}
        if isinstance(tag, FloatTag):
            return {"_t": "float", "_v": tag.value}
        if isinstance(tag, DoubleTag):
            return {"_t": "double", "_v": tag.value}
        if isinstance(tag, StringTag):
            return {"_t": "string", "_v": tag.value}
        if isinstance(tag, ByteArrayTag):
            return {"_t": "byte_array", "_v": list(tag)}
        if isinstance(tag, IntArrayTag):
            return {"_t": "int_array", "_v": list(tag)}
        # Fallback
        return {"_t": "string", "_v": str(tag)}



    def _json_to_tag(self, data: dict):

        t = data.get("_t", "")
        v = data.get("_v")

        if t == "compound":
            return CompoundTag({k: self._json_to_tag(val) for k, val in v.items()})
        if t == "list":
            lt = ListTag()
            for item in v:
                lt.append(self._json_to_tag(item))
            return lt
        if t == "byte":
            return ByteTag(int(v))
        if t == "short":
            return ShortTag(int(v))
        if t == "int":
            return IntTag(int(v))
        if t == "long":
            return LongTag(int(v))
        if t == "float":
            return FloatTag(float(v))
        if t == "double":
            return DoubleTag(float(v))
        if t == "string":
            return StringTag(str(v))
        if t == "byte_array":
            return ByteArrayTag(v)
        if t == "int_array":
            return IntArrayTag(v)
        # Fallback
        return StringTag(str(v))
