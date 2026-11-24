"""Catalogue used by seed_demo. Everything here is fixed so every demo has the
same schools, courses and curriculum. Names are picked from the lists below,
and Faker fills in addresses and phone numbers."""

from decimal import Decimal

LAST_NAMES = [
    "Santos", "Reyes", "Cruz", "Bautista", "Garcia", "Mendoza", "Ramos",
    "Aquino", "Castillo", "Villanueva", "Dela Cruz", "Fernandez", "Gonzales",
    "Lopez", "Torres", "Rivera", "Flores", "Navarro", "Salazar", "Pascual",
    "Domingo", "Mercado", "Aguilar", "Valdez", "Soriano", "Manalo", "Dizon",
    "Tolentino", "Bernardo", "Morales", "Ocampo", "Javier", "Gutierrez",
    "Cabrera", "De Leon", "Evangelista", "Samonte", "Lim", "Tan", "Sy",
]  # fmt: skip

MALE_FIRST_NAMES = [
    "Juan", "Jose", "Miguel", "Paolo", "Carlo", "Mark", "John Paul", "Rafael",
    "Gabriel", "Joshua", "Christian", "Angelo", "Kenneth", "Adrian", "Daniel",
    "Marco", "Luis", "Jerome", "Bryan", "Nathaniel",
]  # fmt: skip

FEMALE_FIRST_NAMES = [
    "Maria", "Angela", "Kristine", "Patricia", "Camille", "Nicole", "Andrea",
    "Bea", "Jasmine", "Mae", "Sofia", "Isabel", "Clarisse", "Danica",
    "Katrina", "Joanna", "Erika", "Bianca", "Trisha", "Precious",
]  # fmt: skip

BARANGAYS = [
    "Poblacion", "San Isidro", "San Roque", "Santa Cruz", "San Jose",
    "Bagong Silang", "Santo Niño", "San Antonio", "Malinis", "Maligaya",
]  # fmt: skip

FS = "FS"
SS = "SS"

SCHOOLS = [
    {"code": "SOC", "name": "School of Computing"},
    {"code": "SBA", "name": "School of Business and Accountancy"},
]

# Departments without a school serve every course
DEPARTMENTS = [
    {"code": "CS", "name": "Computer Science", "school": "SOC"},
    {"code": "ACC", "name": "Accountancy", "school": "SBA"},
    {"code": "GE", "name": "General Education", "school": None},
    {"code": "PE", "name": "Physical Education", "school": None},
]

# Each floor has three lecture rooms and a laboratory
BUILDINGS = [
    {
        "prefix": "ST",
        "name": "Science and Technology Building",
        "floors": 4,
        "school": "SOC",
    },
    {"prefix": "BB", "name": "Business Building", "floors": 3, "school": "SBA"},
]

# code: (title, units, department)
GENERAL_EDUCATION = {
    "GE101": ("Understanding the Self", 3, "GE"),
    "GE102": ("Readings in Philippine History", 3, "GE"),
    "GE103": ("The Contemporary World", 3, "GE"),
    "GE104": ("Mathematics in the Modern World", 3, "GE"),
    "GE105": ("Purposive Communication", 3, "GE"),
    "GE106": ("Art Appreciation", 3, "GE"),
    "GE107": ("Science, Technology and Society", 3, "GE"),
    "GE108": ("Ethics", 3, "GE"),
    "GE109": ("Life and Works of Rizal", 3, "GE"),
    "PE1": ("Movement Competency Training", 2, "PE"),
    "PE2": ("Exercise-based Fitness Activities", 2, "PE"),
    "PE3": ("Individual and Dual Sports", 2, "PE"),
    "PE4": ("Team Sports", 2, "PE"),
    "NSTP1": ("National Service Training Program 1", 3, "GE"),
    "NSTP2": ("National Service Training Program 2", 3, "GE"),
}

# Course subjects are (code, title, units, has_lab). General education
# subjects are referenced by code.
COURSES = [
    {
        "code": "BSCS",
        "name": "Bachelor of Science in Computer Science",
        "school": "SOC",
        "department": "CS",
        "category": "CS",
        "curriculum": {
            (1, FS): [
                ("CS101", "Introduction to Computing", 3, True),
                ("CS102", "Computer Programming 1", 3, True),
                "GE101",
                "GE104",
                "PE1",
                "NSTP1",
            ],
            (1, SS): [
                ("CS103", "Computer Programming 2", 3, True),
                ("CS104", "Discrete Structures 1", 3, False),
                "GE102",
                "GE105",
                "PE2",
                "NSTP2",
            ],
            (2, FS): [
                ("CS201", "Data Structures and Algorithms", 3, True),
                ("CS202", "Discrete Structures 2", 3, False),
                ("CS203", "Object-Oriented Programming", 3, True),
                "GE103",
                "PE3",
            ],
            (2, SS): [
                ("CS204", "Information Management", 3, True),
                ("CS205", "Computer Organization and Architecture", 3, False),
                ("CS206", "Algorithms and Complexity", 3, False),
                "GE106",
                "PE4",
            ],
            (3, FS): [
                ("CS301", "Software Engineering 1", 3, False),
                ("CS302", "Operating Systems", 3, True),
                ("CS303", "Networks and Communications", 3, True),
                ("CS304", "Automata Theory and Formal Languages", 3, False),
                "GE107",
            ],
            (3, SS): [
                ("CS305", "Software Engineering 2", 3, False),
                ("CS306", "Programming Languages", 3, False),
                ("CS307", "Human-Computer Interaction", 3, False),
                ("CS308", "Information Assurance and Security", 3, True),
                "GE108",
            ],
            (4, FS): [
                ("CS401", "Thesis 1", 3, False),
                ("CS402", "Parallel and Distributed Computing", 3, True),
                ("CS403", "Intelligent Systems", 3, True),
                ("CS404", "Social Issues and Professional Practice", 3, False),
                "GE109",
            ],
            (4, SS): [
                ("CS405", "Thesis 2", 3, False),
                ("CS406", "Practicum", 6, False),
                ("CS407", "Mobile Application Development", 3, True),
            ],
        },
    },
    {
        "code": "BSA",
        "name": "Bachelor of Science in Accountancy",
        "school": "SBA",
        "department": "ACC",
        "category": "ACC",
        "curriculum": {
            (1, FS): [
                ("ACC101", "Financial Accounting and Reporting", 3, False),
                ("ECO101", "Microeconomics", 3, False),
                ("MGT101", "Principles of Management", 3, False),
                "GE101",
                "GE104",
                "PE1",
                "NSTP1",
            ],
            (1, SS): [
                ("ACC102", "Conceptual Framework and Accounting Standards", 3, False),
                ("ECO102", "Macroeconomics", 3, False),
                ("BUS101", "Business Mathematics", 3, False),
                "GE102",
                "GE105",
                "PE2",
                "NSTP2",
            ],
            (2, FS): [
                ("ACC201", "Intermediate Accounting 1", 3, False),
                ("ACC202", "Cost Accounting and Control", 3, False),
                ("LAW201", "Law on Obligations and Contracts", 3, False),
                "GE103",
                "PE3",
            ],
            (2, SS): [
                ("ACC203", "Intermediate Accounting 2", 3, False),
                ("FIN201", "Financial Management", 3, False),
                ("LAW202", "Business Laws and Regulations", 3, False),
                "GE106",
                "PE4",
            ],
            (3, FS): [
                ("ACC301", "Intermediate Accounting 3", 3, False),
                ("ACC302", "Auditing and Assurance Principles", 3, False),
                ("TAX301", "Income Taxation", 3, False),
                ("ACC303", "Accounting Information Systems", 3, True),
                "GE107",
            ],
            (3, SS): [
                ("ACC304", "Advanced Financial Accounting 1", 3, False),
                ("ACC305", "Auditing in a CIS Environment", 3, True),
                ("TAX302", "Business Taxation", 3, False),
                ("ACC306", "Strategic Cost Management", 3, False),
                "GE108",
            ],
            (4, FS): [
                ("ACC401", "Advanced Financial Accounting 2", 3, False),
                ("ACC402", "Auditing in Specialized Industries", 3, False),
                ("ACC403", "Accounting Research Methods", 3, False),
                "GE109",
            ],
            (4, SS): [
                ("ACC404", "Accounting Internship", 6, False),
                ("ACC405", "Integrated Review in Financial Accounting", 3, False),
                ("ACC406", "Integrated Review in Auditing", 3, False),
            ],
        },
    },
]

PREREQUISITES = {
    "CS103": ["CS102"],
    "CS201": ["CS103"],
    "CS203": ["CS103"],
    "CS204": ["CS201"],
    "CS206": ["CS201", "CS202"],
    "CS302": ["CS205"],
    "CS305": ["CS301"],
    "CS405": ["CS401"],
    "ACC102": ["ACC101"],
    "ACC201": ["ACC102"],
    "ACC203": ["ACC201"],
    "ACC301": ["ACC203"],
    "ACC304": ["ACC301"],
    "ACC401": ["ACC304"],
    "TAX302": ["TAX301"],
    "PE2": ["PE1"],
    "NSTP2": ["NSTP1"],
}

# Per-unit tuition for the current school year. Earlier years are a bit cheaper.
TUITION_PER_UNIT = {
    "professional": Decimal("1450.00"),
    "general": Decimal("1200.00"),
}
YEARLY_TUITION_INCREASE = Decimal("0.05")

LABORATORY_FEE = Decimal("1800.00")

MISCELLANEOUS_FEES = [
    ("REG", "Registration", Decimal("1500.00")),
    ("LIB", "Library", Decimal("1200.00")),
    ("MED", "Medical and Dental", Decimal("650.00")),
    ("ATH", "Athletics", Decimal("500.00")),
    ("STA", "Student Activities", Decimal("450.00")),
    ("GUI", "Guidance and Counseling", Decimal("400.00")),
]

OTHER_FEES = [
    ("ID", "Student ID", Decimal("250.00")),
    ("INS", "Accident Insurance", Decimal("200.00")),
    ("HBK", "Student Handbook", Decimal("150.00")),
]

DISCOUNTS = [
    {"ref_id": "1", "name": "Academic Scholarship", "percentage": Decimal("50.00")},
    {"ref_id": "2", "name": "Sibling Discount", "percentage": Decimal("10.00")},
]

# Two meetings a week, 90 minutes each
DAY_PAIRS = [("M", "W"), ("T", "TH"), ("F", "S")]
TIME_SLOTS = [
    ("07:30", "09:00"),
    ("09:00", "10:30"),
    ("10:30", "12:00"),
    ("13:00", "14:30"),
    ("14:30", "16:00"),
    ("16:00", "17:30"),
]
