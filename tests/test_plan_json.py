import unittest

from lalo.fixtures import iron_man_plan, spider_man_plan
from lalo.plan_json import (
    CharacterPlanCodecError,
    character_plan_from_dict,
    character_plan_from_json,
    character_plan_to_dict,
    character_plan_to_json,
)


class CharacterPlanJsonTests(unittest.TestCase):
    def test_golden_plans_round_trip_exactly(self) -> None:
        for plan in (spider_man_plan(), iron_man_plan()):
            self.assertEqual(character_plan_from_json(character_plan_to_json(plan)), plan)
            self.assertEqual(character_plan_from_dict(character_plan_to_dict(plan)), plan)

    def test_encoding_is_deterministic_compact_and_utf8(self) -> None:
        plan = spider_man_plan()
        encoded = character_plan_to_json(plan)

        self.assertEqual(encoded, character_plan_to_json(plan))
        self.assertNotIn(": ", encoded)
        self.assertNotIn(", ", encoded)
        self.assertEqual(character_plan_from_json(encoded.encode("utf-8")), plan)

    def test_rejects_unknown_missing_and_duplicate_keys(self) -> None:
        value = character_plan_to_dict(spider_man_plan())
        value["extra"] = True
        with self.assertRaisesRegex(CharacterPlanCodecError, "unknown"):
            character_plan_from_dict(value)

        value = character_plan_to_dict(spider_man_plan())
        del value["name"]
        with self.assertRaisesRegex(CharacterPlanCodecError, "missing"):
            character_plan_from_dict(value)

        with self.assertRaisesRegex(CharacterPlanCodecError, "duplicate object key"):
            character_plan_from_json('{"name":"one","name":"two"}')

    def test_rejects_wrong_types_boolean_integers_and_invalid_face(self) -> None:
        value = character_plan_to_dict(spider_man_plan())
        value["palette"][0]["id"] = True
        with self.assertRaisesRegex(CharacterPlanCodecError, "must be an integer"):
            character_plan_from_dict(value)

        value = character_plan_to_dict(spider_man_plan())
        value["parts"][0]["surfaces"][0]["face"] = "inside"
        with self.assertRaisesRegex(CharacterPlanCodecError, "invalid value"):
            character_plan_from_dict(value)

        with self.assertRaisesRegex(CharacterPlanCodecError, "must be an object"):
            character_plan_from_json("[]")

    def test_existing_semantic_validation_rejects_invalid_nested_plan(self) -> None:
        value = character_plan_to_dict(spider_man_plan())
        value["palette"][0]["srgb"] = "red"

        with self.assertRaisesRegex(CharacterPlanCodecError, "#RRGGBB"):
            character_plan_from_dict(value)

    def test_rejects_invalid_json_and_non_utf8_bytes(self) -> None:
        for payload in ("{", b"\xff"):
            with self.assertRaises(CharacterPlanCodecError):
                character_plan_from_json(payload)


if __name__ == "__main__":
    unittest.main()
