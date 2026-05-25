import unittest

from contact_scraper import scrape_contact_lines


CONTACT_LINES = [
    "ChevronDownXFat",
    "Jane Carter",
    "Account Support",
    "Mail",
    "jane.carter@example.invalid",
    "Phone",
    "+49 89 111",
    "Main Office",
    "more information",
    "Consultation Tuesday 10-12",
    "Room 201",
    "less information",
    "Icon",
    "Max Reed",
    "Records Office",
    "max.reed@example.invalid",
]


class ContactScraperTests(unittest.TestCase):
    def test_renders_contact_fields_and_filters_chrome_lines(self):
        output = scrape_contact_lines(CONTACT_LINES)

        self.assertIn("Name: Jane Carter", output)
        self.assertIn("Role: Account Support", output)
        self.assertIn("Email: jane.carter@example.invalid", output)
        self.assertIn("Phone: +49 89 111", output)
        self.assertIn("Location: Main Office", output)
        self.assertIn("Hours: Consultation Tuesday 10-12 Room 201", output)
        self.assertIn("Name: Max Reed", output)
        self.assertIn("Role: Records Office", output)
        self.assertNotIn("Chevron", output)
        self.assertNotIn("Icon", output)


if __name__ == "__main__":
    unittest.main()
