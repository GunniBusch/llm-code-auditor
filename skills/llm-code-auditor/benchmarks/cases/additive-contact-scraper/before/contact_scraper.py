import re


def scrape_contact_lines(lines):
    try:
        contacts = []
        current = {}
        in_hours = False
        hours = []

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("Chevron"):
                continue
            if line.startswith("Icon"):
                continue
            if line in {"XFat", "TOP", "Search"}:
                continue
            if "virtual assistant" in line.lower() or "support center" in line.lower():
                continue

            if "more information" in line.lower():
                in_hours = True
                hours = []
                continue

            if "less information" in line.lower():
                in_hours = False
                if hours:
                    current["hours"] = " ".join(hours)
                if "name" in current:
                    contacts.append(current)
                current = {}
                hours = []
                continue

            if in_hours:
                if "@" in line and "example.invalid" in line:
                    current["email"] = line
                    continue
                if (
                    line.startswith("+49")
                    or line.startswith("+ 49")
                    or line.startswith("089")
                    or line.startswith("(089)")
                    or re.match(r"^\+?\d[\d\s\-\(\)]+$", line)
                ):
                    if "phone" not in current:
                        current["phone"] = line
                    continue
                hours.append(line)
                continue

            if line in {"Account Support", "Records Office"}:
                if "name" in current and "role" not in current:
                    current["role"] = line
                continue

            if "Office" in line:
                current["location"] = line
                continue

            if (
                re.match(r"^[A-Z][a-z]+(\s+[A-Z][a-z]+)+$", line)
                and "@" not in line
                and "Management" not in line
            ):
                if "name" in current:
                    contacts.append(current)
                current = {"name": line}
                continue

            if line in {"Mail", "Phone"}:
                continue

            if (
                "name" in current
                and "role" not in current
                and "@" not in line
                and not line.startswith("+")
            ):
                current["role"] = line
                continue

            if "@" in line and "example.invalid" in line:
                current["email"] = line
                continue

            if (
                line.startswith("+49")
                or line.startswith("+ 49")
                or line.startswith("089")
                or line.startswith("(089)")
                or re.match(r"^\+?\d[\d\s\-\(\)]+$", line)
            ):
                if "phone" not in current:
                    current["phone"] = line
                continue

        if "name" in current:
            contacts.append(current)

        output = ""
        for contact in contacts:
            output += f"Name: {contact.get('name', 'N/A')}\n"
            if "role" in contact:
                output += f"Role: {contact['role']}\n"
            if "email" in contact:
                output += f"Email: {contact['email']}\n"
            if "phone" in contact:
                output += f"Phone: {contact['phone']}\n"
            if "location" in contact:
                output += f"Location: {contact['location']}\n"
            if "hours" in contact:
                output += f"Hours: {contact['hours']}\n"
            output += "\n"
        return output.strip()
    except Exception:
        return ""
