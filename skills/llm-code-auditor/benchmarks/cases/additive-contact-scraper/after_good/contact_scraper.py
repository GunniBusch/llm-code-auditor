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
class ContactParser:
    contacts: list[Contact] = field(default_factory=list)
    current: Contact | None = None
    collecting_hours: bool = False
    hours: list[str] = field(default_factory=list)

    def parse(self, lines):
        for line in clean_contact_lines(lines):
            CONTACT_EVENTS[classify_contact_line(line)](self, line)
        self.finish_current()
        return self.contacts

    def finish_current(self, _line=""):
        if self.current is not None:
            if self.hours:
                self.current.hours = " ".join(self.hours)
            self.contacts.append(self.current)
        self.current = None
        self.collecting_hours = False
        self.hours = []

    def start_contact(self, line):
        self.finish_current()
        self.current = Contact(name=line)

    def start_hours(self, _line):
        self.collecting_hours = True
        self.hours = []

    def end_hours(self, _line):
        if self.current is not None and self.hours:
            self.current.hours = " ".join(self.hours)
        self.collecting_hours = False
        self.hours = []

    def set_field(self, field_name, line):
        if self.current is not None:
            setattr(self.current, field_name, line)

    def add_detail(self, line):
        if self.current is not None and self.collecting_hours:
            self.hours.append(line)
        elif self.current is not None and not self.current.role:
            self.current.role = line


def scrape_contact_lines(lines):
    return "\n\n".join(render_contact(contact) for contact in ContactParser().parse(lines))


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


def classify_contact_line(line):
    for kind, matches in CONTACT_LINE_RULES:
        if matches(line):
            return kind
    return "detail"


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


CONTACT_EVENTS = {
    "name": ContactParser.start_contact,
    "hours-start": ContactParser.start_hours,
    "hours-end": ContactParser.end_hours,
    "role": lambda parser, line: parser.set_field("role", line),
    "email": lambda parser, line: parser.set_field("email", line),
    "phone": lambda parser, line: parser.set_field("phone", line),
    "location": lambda parser, line: parser.set_field("location", line),
    "detail": ContactParser.add_detail,
}

CONTACT_LINE_RULES = (
    ("hours-start", lambda line: line.lower() == "more information"),
    ("hours-end", lambda line: line.lower() == "less information"),
    ("role", lambda line: line in ROLE_LINES),
    ("location", lambda line: "Office" in line),
    ("name", is_person_name),
    ("email", is_email),
    ("phone", is_phone),
)
