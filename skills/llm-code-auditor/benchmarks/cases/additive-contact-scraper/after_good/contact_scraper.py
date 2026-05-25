from dataclasses import dataclass, field
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


@dataclass
class ContactParseState:
    contacts: list[Contact] = field(default_factory=list)
    current: Contact | None = None
    collecting_hours: bool = False
    hours: list[str] = field(default_factory=list)

    def finish_current(self):
        if self.current:
            if self.hours:
                self.current.hours = " ".join(self.hours)
            self.contacts.append(self.current)
        self.current = None
        self.collecting_hours = False
        self.hours = []


def scrape_contact_lines(lines):
    contacts = parse_contacts(clean_contact_lines(lines))
    return "\n\n".join(render_contact(contact) for contact in contacts)


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


def parse_contacts(lines):
    state = ContactParseState()
    for line in lines:
        apply_contact_line(state, classify_contact_line(line), line)
    state.finish_current()
    return state.contacts


def classify_contact_line(line):
    if line.lower() == "more information":
        return "hours-start"
    if line.lower() == "less information":
        return "hours-end"
    if line in ROLE_LINES:
        return "role"
    if "Office" in line:
        return "location"
    if is_person_name(line):
        return "name"
    if is_email(line):
        return "email"
    if is_phone(line):
        return "phone"
    return "detail"


def apply_contact_line(state, kind, line):
    CONTACT_LINE_HANDLERS[kind](state, line)


def start_contact(state, line):
    state.finish_current()
    state.current = Contact(name=line)


def start_hours(state, _line):
    state.collecting_hours = True
    state.hours = []


def end_hours(state, _line):
    if state.current and state.hours:
        state.current.hours = " ".join(state.hours)
    state.collecting_hours = False
    state.hours = []


def set_role(state, line):
    if state.current:
        state.current.role = line


def set_email(state, line):
    if state.current:
        state.current.email = line


def set_phone(state, line):
    if state.current:
        state.current.phone = line


def set_location(state, line):
    if state.current:
        state.current.location = line


def add_detail(state, line):
    if state.current and state.collecting_hours:
        state.hours.append(line)
    elif state.current and not state.current.role:
        state.current.role = line


CONTACT_LINE_HANDLERS = {
    "hours-start": start_hours,
    "hours-end": end_hours,
    "name": start_contact,
    "role": set_role,
    "email": set_email,
    "phone": set_phone,
    "location": set_location,
    "detail": add_detail,
}


def is_person_name(line):
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
    return "\n".join(f"{label}: {value}" for label, value in fields if value).strip()
