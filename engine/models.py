"""Typed models shared by the parser, the rules engine and the app.

Nothing here paraphrases policy text. Clause wording is always loaded from the
parsed policy files (BUILD_SPEC 0.5).
"""

from __future__ import annotations

from datetime import date
from enum import Enum, StrEnum

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# Verdict status and approval kind
# --------------------------------------------------------------------------


class Status(StrEnum):
    """The four verdicts in BUILD_SPEC 5."""

    ALLOWED = "ALLOWED"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"
    NOT_PERMITTED = "NOT_PERMITTED"
    PROHIBITED = "PROHIBITED"


# BUILD_SPEC 5: PROHIBITED > NOT_PERMITTED > NEEDS_APPROVAL > ALLOWED
_STATUS_SEVERITY: dict[Status, int] = {
    Status.ALLOWED: 0,
    Status.NEEDS_APPROVAL: 1,
    Status.NOT_PERMITTED: 2,
    Status.PROHIBITED: 3,
}


def most_severe(statuses: list[Status]) -> Status:
    """The most severe status, or ALLOWED when nothing more severe fired."""
    return max(statuses, key=lambda s: _STATUS_SEVERITY[s], default=Status.ALLOWED)


class ApprovalKind(StrEnum):
    """Which kind of human approval a NEEDS_APPROVAL verdict calls for.

    Not named in BUILD_SPEC 5's field list, but BUILD_SPEC 6 distinguishes
    "NEEDS_APPROVAL (one-time)" from "NEEDS_APPROVAL (per message)" for
    scenarios 8, 9 and 10. See OPEN_QUESTIONS Q3.
    """

    NONE = "none"
    ONE_TIME_USE_CASE = "one_time_use_case"
    PER_ACTION = "per_action"


_APPROVAL_SEVERITY: dict[ApprovalKind, int] = {
    ApprovalKind.NONE: 0,
    ApprovalKind.ONE_TIME_USE_CASE: 1,
    ApprovalKind.PER_ACTION: 2,
}


def strictest_approval(kinds: list[ApprovalKind]) -> ApprovalKind:
    """Per-action approval beats a one-time use-case approval."""
    return max(kinds, key=lambda k: _APPROVAL_SEVERITY[k], default=ApprovalKind.NONE)


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------


class DataClass(StrEnum):
    PUBLIC = "Public"
    INTERNAL = "Internal"
    CONFIDENTIAL = "Confidential"
    RESTRICTED = "Restricted"
    SECRETS = "Secrets"


class DataKind(StrEnum):
    """What makes the data what it is, so the verdict can cite 7.4, 7.5 or B.2.3."""

    NONE = "none"
    ORDINARY_PERSONAL = "ordinary_personal"
    SENSITIVE_PERSONAL = "sensitive_personal"
    HR_HEALTH_RECORD = "hr_health_record"
    CLIENT_INFO = "client_info"


class Tool(StrEnum):
    TIER_A = "A"
    TIER_B = "B"
    TIER_C = "C"
    SELF_HOSTED = "self_hosted"


class Host(StrEnum):
    """Where a self-hosted model runs (B.1.3, 2.3)."""

    ORG_CLOUD = "org_cloud"
    MANAGED_LAPTOP = "managed_laptop"
    PERSONAL_DEVICE = "personal_device"


class EffectiveTier(StrEnum):
    """Tool tier after resolving a self-hosted model's host.

    PERSONAL_SELFHOSTED is deliberately distinct from TIER_C. See
    OPEN_QUESTIONS Q4 for why that choice decides scenario 20.
    """

    A = "A"
    B = "B"
    C = "C"
    PERSONAL_SELFHOSTED = "personal_selfhosted"


class Activity(StrEnum):
    DRAFTING = "drafting"
    CODING = "coding"
    DECISION_ABOUT_PERSON = "decision_about_person"
    CHATBOT = "chatbot"
    PUBLISHING = "publishing"
    SYNTHETIC_MEDIA = "synthetic_media"
    MONITORING_EMPLOYEES = "monitoring_employees"
    EMOTION_RECOGNITION = "emotion_recognition"
    FATIGUE_DETECTION = "fatigue_detection"
    SAFETY_CRITICAL = "safety_critical"
    CONNECTING_SYSTEMS = "connecting_systems"
    NOTETAKER = "notetaker"
    AGENT = "agent"


class AgentAction(StrEnum):
    READ = "read"
    WRITE = "write"
    PAY = "pay"
    DELETE = "delete"
    MESSAGE_EXTERNAL = "message_external"
    PRODUCTION_CHANGE = "production_change"
    ADD_PAYEE = "add_payee"
    ADD_RECIPIENT = "add_recipient"


class MeetingType(StrEnum):
    ORDINARY = "ordinary"
    LEGAL_COUNSEL = "legal_counsel"
    HR_CASEWORK = "hr_casework"
    BOARD_EXEC = "board_exec"
    UNDISCLOSED_DEAL = "undisclosed_deal"


class Inputs(BaseModel):
    """What the visitor picks. Conditional flags default to None (not asked)."""

    data_class: DataClass
    tool: Tool
    activity: Activity

    data_kind: DataKind = DataKind.NONE
    host: Host | None = None

    human_review: bool | None = None
    hiring: bool = False
    client_contract_allows: bool | None = None
    training_or_finetuning: bool = False
    sexual_or_intimate: bool = False

    agent_action: AgentAction | None = None
    recipient_on_allowlist: bool | None = None
    payee_on_allowlist: bool | None = None
    within_caps: bool | None = None

    meeting_type: MeetingType | None = None

    @property
    def effective_tier(self) -> EffectiveTier:
        """The v1.5 tier resolution. See `resolve_effective_tier`."""
        return resolve_effective_tier(self, "v1_5")

    def context(self, effective_tier: EffectiveTier) -> dict[str, str | bool | None]:
        """Flatten to the primitives the `when:` matcher compares against.

        The tier is passed in rather than computed, because how a self-hosted
        model is tiered is itself a policy question that changed between
        versions.
        """
        ctx: dict[str, str | bool | None] = {}
        for name in self.__class__.model_fields:
            value = getattr(self, name)
            ctx[name] = value.value if isinstance(value, Enum) else value
        ctx["effective_tier"] = effective_tier.value
        return ctx


def resolve_effective_tier(inputs: Inputs, version: str) -> EffectiveTier:
    """Resolve tool + host to a tier, which differs by policy version.

    **v1.5** (B.1.3, 2.3): organizational servers or the organization's cloud
    tenancy are the only hosts eligible for Tier A; a managed company laptop
    is Tier B at most; a personal or unmanaged device gets its own value,
    deliberately distinct from Tier C (OPEN_QUESTIONS Q4).

    **v1.0** has no self-hosted or open-weight criteria at all. Its only Tier
    A test is 7.5, which is vendor-contract shaped ("an enterprise contract,
    no training on our inputs..."), so a locally run model cannot meet it and
    falls to Tier C, "anything not assessed". Separate criteria for
    self-hosted models arrived in v1.1 as B.1.3.
    """
    if inputs.tool is not Tool.SELF_HOSTED:
        return EffectiveTier(inputs.tool.value)
    if version == "v1_0":
        return EffectiveTier.C
    match inputs.host:
        case Host.ORG_CLOUD:
            return EffectiveTier.A
        case Host.MANAGED_LAPTOP:
            return EffectiveTier.B
        case _:
            # No host stated is treated as the least safe case.
            return EffectiveTier.PERSONAL_SELFHOSTED


# --------------------------------------------------------------------------
# Policy and backing
# --------------------------------------------------------------------------


class Clause(BaseModel):
    """One citable clause, with its text exactly as the policy file has it."""

    id: str
    part: str | None = None
    section: str | None = None
    section_title: str | None = None
    text: str

    @property
    def sort_key(self) -> tuple[int, tuple[int | str, ...]]:
        """Order Part A numerically, then B, C, D."""
        head = self.id.split(".")[0]
        group = {"B": 1, "C": 2}.get(head, 0 if head.isdigit() else 3)
        parts: list[int | str] = [int(p) if p.isdigit() else p for p in self.id.split(".")]
        return group, tuple(parts)


class Table(BaseModel):
    """A markdown table parsed into headers and rows."""

    headers: list[str]
    rows: list[list[str]]

    @property
    def shape(self) -> tuple[int, int]:
        """(data rows, data columns), excluding the header row and label column."""
        return len(self.rows), max(0, len(self.headers) - 1)


class BasisType(StrEnum):
    LAW = "law"
    STANDARD = "standard"
    OUR_CHOICE = "our_choice"


class Basis(BaseModel):
    """Why a rule exists. Context only: it never changes a verdict (BUILD_SPEC 7)."""

    clause: str
    type: BasisType
    source: str
    jurisdiction: str | None = None
    status: str | None = None
    checked: date
    note: str | None = None

    def is_stale(self, today: date, max_age_days: int = 90) -> bool:
        return (today - self.checked).days > max_age_days


class StaffSummary(BaseModel):
    """The one-page summary. Absent in v1.0, which returns empty lists."""

    always: list[str] = Field(default_factory=list)
    ask_first: list[str] = Field(default_factory=list)
    never: list[str] = Field(default_factory=list)
    #: The closing line ("Questions: [AI governance contact]. ..."), which
    #: carries one of the policy's template fields.
    footer: str = ""

    @property
    def is_empty(self) -> bool:
        return not (self.always or self.ask_first or self.never)


class Policy(BaseModel):
    """A parsed policy version."""

    version: str
    clauses: dict[str, Clause]
    tables: dict[str, list[Table]]
    staff_summary: StaffSummary
    #: The document's own header fields (Policy ID, Version, Organization,
    #: Owner...), in file order. Several hold template placeholders.
    front_matter: dict[str, str] = Field(default_factory=dict)
    #: "Changes in version N" tables, keyed by version ("1.5", "1.4", ...).
    #: Newest first, which is the order the policy file itself uses.
    changelogs: dict[str, Table] = Field(default_factory=dict)

    def clause(self, clause_id: str) -> Clause:
        if clause_id not in self.clauses:
            raise KeyError(f"clause {clause_id!r} is not in policy {self.version}")
        return self.clauses[clause_id]

    def table(self, owner_id: str, index: int = 0) -> Table:
        tables = self.tables.get(owner_id, [])
        if len(tables) <= index:
            raise KeyError(f"no table {index} under {owner_id!r} in policy {self.version}")
        return tables[index]


# --------------------------------------------------------------------------
# Rules and verdict
# --------------------------------------------------------------------------


class Rule(BaseModel):
    """One rule from a rules YAML file."""

    id: str
    when: dict
    status: Status
    approval_kind: ApprovalKind = ApprovalKind.NONE
    reason: str
    clauses: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    try_instead: str | None = None


class Verdict(BaseModel):
    """The answer shown on the card."""

    status: Status
    approval_kind: ApprovalKind = ApprovalKind.NONE
    reasons: list[str] = Field(default_factory=list)
    clauses: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    try_instead: str | None = None
    basis: list[Basis] = Field(default_factory=list)
    fired_rules: list[str] = Field(default_factory=list)

    #: The clauses of the rules that fired at this verdict's own status: the
    #: ones the answer rests on. `clauses` holds these and the supporting ones
    #: together, which is right for a drawer and wrong for a row of chips,
    #: where seven equal-looking chips hide the one doing the work.
    decisive_clauses: list[str] = Field(default_factory=list)
