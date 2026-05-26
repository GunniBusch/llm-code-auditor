from dataclasses import dataclass
import re


NOISE_LINES = {"XFat", "TOP", "Search", "Mail", "Phone"}
ROLE_LINES = {"Account Support", "Records Office"}


@dataclass
class Contact:
    name: str
    role: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    hours: str = ""


def scrape_contact_lines(lines):
    return "\n\n".join(render_contact(contact) for contact in parse_contacts(lines))


def parse_contacts(lines):
    contacts = []
    current, hours, collecting_hours = None, [], False

    for line in clean_contact_lines(lines):
        if is_person_name(line):
            current, hours, collecting_hours = finish_contact(contacts, current, hours)
            current = Contact(name=line)
        elif current is not None:
            current, hours, collecting_hours = apply_contact_line(
                current, line, hours, collecting_hours
            )

    finish_contact(contacts, current, hours)
    return contacts


def finish_contact(contacts, contact, hours):
    if contact is not None:
        if hours:
            contact.hours = " ".join(hours)
        contacts.append(contact)
    return None, [], False


def apply_contact_line(contact, line, hours, collecting_hours):
    lowered = line.lower()
    if lowered == "more information":
        return contact, [], True
    if lowered == "less information":
        return contact, hours, False
    if collecting_hours:
        hours.append(line)
    else:
        apply_contact_detail(contact, line)
    return contact, hours, collecting_hours


def clean_contact_lines(lines):
    return [
        line
        for raw_line in lines
        if (line := raw_line.strip()) and not is_noise_line(line)
    ]


def is_noise_line(line):
    return (
        line in NOISE_LINES
        or line.startswith(("Chevron", "Icon"))
        or "virtual assistant" in line.lower()
        or "support center" in line.lower()
    )


def apply_contact_detail(contact, line):
    if line in ROLE_LINES and not contact.role:
        contact.role = line
    elif is_email(line):
        contact.email = line
    elif is_phone(line) and not contact.phone:
        contact.phone = line
    elif "Office" in line:
        contact.location = line
    elif not contact.role:
        contact.role = line


def is_person_name(line):
    if line in ROLE_LINES or "Office" in line:
        return False
    return bool(re.match(r"^[A-Z][a-z]+(\s+[A-Z][a-z]+)+$", line))


def is_email(line):
    return "@" in line and "example.invalid" in line


def is_phone(line):
    return line.startswith(("+49", "+ 49", "089", "(089)")) or bool(
        re.match(r"^\+?\d[\d\s\-\(\)]+$", line)
    )


def render_contact(contact):
    fields = [
        ("Name", contact.name),
        ("Role", contact.role),
        ("Email", contact.email),
        ("Phone", contact.phone),
        ("Location", contact.location),
        ("Hours", contact.hours),
    ]
    return "\n".join(f"{label}: {value}" for label, value in fields if value)
