from enum import Enum
from dataclasses import dataclass
from typing import Any

from app.schemas.diagnosis import RiskLevel
from app.core.logging import get_logger
RISK_LEVEL_RANK = {
    RiskLevel.SAFE: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MODERATE: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}

logger = get_logger(__name__)


class SafetyRiskCategory(str, Enum):
    BATTERY_SWELLING = "battery_swelling"
    BURNING_SMELL = "burning_smell"
    SMOKE = "smoke"
    SPARKS = "sparks"
    ELECTRICAL_SHOCK = "electrical_shock"
    WATER_DAMAGE = "water_damage"
    HIGH_VOLTAGE = "high_voltage"
    EXPOSED_WIRING = "exposed_wiring"
    OVERHEATING = "overheating"
    BATTERY_LEAKAGE = "battery_leakage"
    CAPACITOR_DISCHARGE = "capacitor_discharge"
    STRUCTURAL_DAMAGE = "structural_damage"


CRITICAL_KEYWORDS = {
    SafetyRiskCategory.BATTERY_SWELLING: [
        "swollen", "bulging", "expanded", "puffed", "battery swelling",
        "battery bulge", "back coming off", "screen lifting"
    ],
    SafetyRiskCategory.BURNING_SMELL: [
        "burning smell", "burnt smell", "smells like burning",
        "electrical burning", "ozone smell", "melting plastic"
    ],
    SafetyRiskCategory.SMOKE: [
        "smoke", "smoking", "white smoke", "black smoke", "smoke coming"
    ],
    SafetyRiskCategory.SPARKS: [
        "spark", "sparking", "sparks", "arcing", "electrical arc"
    ],
    SafetyRiskCategory.ELECTRICAL_SHOCK: [
        "shock", "electric shock", "zapped", "tingling", "electricity"
    ],
    SafetyRiskCategory.WATER_DAMAGE: [
        "water damage", "liquid damage", "spilled", "dropped in water",
        "submerged", "wet inside", "moisture", "corrosion"
    ],
    SafetyRiskCategory.HIGH_VOLTAGE: [
        "high voltage", "power supply", "capacitor", "flyback",
        "crt", "tv repair", "monitor repair", "mains voltage"
    ],
    SafetyRiskCategory.EXPOSED_WIRING: [
        "exposed wire", "bare wire", "frayed cord", "damaged cord",
        "wire showing", "insulation damaged"
    ],
    SafetyRiskCategory.OVERHEATING: [
        "overheating", "very hot", "extremely hot", "too hot to touch",
        "thermal shutdown", "burning hot"
    ],
    SafetyRiskCategory.BATTERY_LEAKAGE: [
        "leaking battery", "battery leak", "acid leak", "fluid leaking",
        "white powder", "corrosion on battery"
    ],
    SafetyRiskCategory.CAPACITOR_DISCHARGE: [
        "discharge capacitor", "capacitor discharge", "bleeder resistor"
    ],
    SafetyRiskCategory.STRUCTURAL_DAMAGE: [
        "cracked screen", "cracked case", "bent frame", "physical damage",
        "dropped", "crushed", "punctured"
    ],
}

ESCALATION_MESSAGES = {
    SafetyRiskCategory.BATTERY_SWELLING: (
        "A swollen battery is a serious fire and explosion hazard. "
        "STOP using the device immediately. Do not charge it. "
        "Do not attempt to puncture, compress, or remove the battery yourself. "
        "Contact a qualified repair technician or the manufacturer for safe battery replacement."
    ),
    SafetyRiskCategory.BURNING_SMELL: (
        "A burning smell indicates electrical failure or overheating components. "
        "Unplug the device immediately. Do not continue using it. "
        "This requires professional diagnosis and repair."
    ),
    SafetyRiskCategory.SMOKE: (
        "Smoke indicates active electrical fire risk. "
        "Unplug immediately if safe to do so. Evacuate if smoke is significant. "
        "Contact emergency services if there is active fire. "
        "Do not attempt to troubleshoot a smoking device."
    ),
    SafetyRiskCategory.SPARKS: (
        "Sparks or arcing indicate dangerous electrical faults. "
        "Unplug immediately. Do not use the device. "
        "Professional repair is required."
    ),
    SafetyRiskCategory.ELECTRICAL_SHOCK: (
        "Electrical shock indicates a serious safety fault. "
        "Unplug the device immediately. Do not touch exposed metal parts. "
        "Have the device inspected by a qualified electrician or technician before any further use."
    ),
    SafetyRiskCategory.WATER_DAMAGE: (
        "Water damage can cause short circuits, corrosion, and delayed failures. "
        "Do not power on a wet device. Do not charge it. "
        "Professional cleaning and assessment is recommended before attempting use."
    ),
    SafetyRiskCategory.HIGH_VOLTAGE: (
        "TVs and monitors contain high-voltage components that can retain lethal charge "
        "even when unplugged. Internal capacitors can store dangerous energy for extended periods. "
        "NEVER open a TV or monitor casing. All internal repairs must be performed by qualified technicians."
    ),
    SafetyRiskCategory.EXPOSED_WIRING: (
        "Exposed wiring presents shock and fire hazards. "
        "Do not use devices with damaged cords or exposed conductors. "
        "Replace the cord or have it professionally repaired."
    ),
    SafetyRiskCategory.OVERHEATING: (
        "Extreme overheating can indicate failing components or thermal management failure. "
        "Stop using the device. Allow it to cool completely. "
        "If overheating recurs, professional service is needed."
    ),
    SafetyRiskCategory.BATTERY_LEAKAGE: (
        "Battery leakage is corrosive and toxic. "
        "Avoid contact with leaked material. Wash hands if exposed. "
        "Do not attempt to clean or continue using the device. "
        "Professional disposal and repair required."
    ),
    SafetyRiskCategory.CAPACITOR_DISCHARGE: (
        "Capacitor discharge procedures are dangerous and can cause severe injury or death. "
        "NEVER attempt to discharge capacitors in consumer electronics. "
        "This must only be done by trained professionals with proper equipment."
    ),
    SafetyRiskCategory.STRUCTURAL_DAMAGE: (
        "Structural damage may compromise safety systems, battery integrity, or insulation. "
        "Do not use devices with cracked cases, bent frames, or punctured enclosures. "
        "Professional assessment required."
    ),
}


@dataclass
class SafetyScreeningResult:
    safe: bool
    risk_level: RiskLevel
    detected_risks: list[SafetyRiskCategory]
    escalation_message: str | None
    technician_required: bool
    technician_reason: str | None


class SafetyService:
    def screen_user_input(self, problem_description: str, device_category: str) -> SafetyScreeningResult:
        text = problem_description.lower()
        detected = []

        for category, keywords in CRITICAL_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                detected.append(category)

        if not detected:
            return SafetyScreeningResult(
                safe=True,
                risk_level=RiskLevel.SAFE,
                detected_risks=[],
                escalation_message=None,
                technician_required=False,
                technician_reason=None,
            )

        max_risk = RiskLevel.SAFE
        messages = []
        technician_required = False
        reasons = []

        for risk in detected:
            if risk in (SafetyRiskCategory.SMOKE, SafetyRiskCategory.SPARKS, 
                       SafetyRiskCategory.ELECTRICAL_SHOCK, SafetyRiskCategory.BATTERY_SWELLING):
                max_risk = RiskLevel.CRITICAL
            elif risk in (
            SafetyRiskCategory.BURNING_SMELL,
            SafetyRiskCategory.HIGH_VOLTAGE,
            SafetyRiskCategory.BATTERY_LEAKAGE,
            SafetyRiskCategory.CAPACITOR_DISCHARGE,
        ):
                
                if RISK_LEVEL_RANK[RiskLevel.HIGH] > RISK_LEVEL_RANK[max_risk]:
                    max_risk = RiskLevel.HIGH

            elif risk in (
            SafetyRiskCategory.WATER_DAMAGE,
            SafetyRiskCategory.EXPOSED_WIRING,
            SafetyRiskCategory.OVERHEATING,
        ):
                if RISK_LEVEL_RANK[RiskLevel.MODERATE] > RISK_LEVEL_RANK[max_risk]:
                    max_risk = RiskLevel.MODERATE

            messages.append(ESCALATION_MESSAGES.get(risk, ""))
            technician_required = True
            reasons.append(risk.value.replace("_", " ").title())

        if device_category == "tv" and any(r in detected for r in 
            [SafetyRiskCategory.HIGH_VOLTAGE, SafetyRiskCategory.CAPACITOR_DISCHARGE]):
            max_risk = RiskLevel.CRITICAL
            technician_required = True

        return SafetyScreeningResult(
            safe=max_risk in (RiskLevel.SAFE, RiskLevel.LOW),
            risk_level=max_risk,
            detected_risks=detected,
            escalation_message="\n\n".join(messages) if messages else None,
            technician_required=technician_required,
            technician_reason="; ".join(reasons) if reasons else None,
        )

    def validate_ai_response(self, result: Any) -> tuple[bool, list[str]]:
        errors = []

        if not hasattr(result, "safe_steps") or not result.safe_steps:
            errors.append("No safe steps provided")
            return False, errors

        for step in result.safe_steps:
            if step.risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                errors.append(f"Step {step.step} has unsafe risk level: {step.risk}")
                return False, errors

            dangerous_keywords = [
                "open the", "disassemble", "take apart", "remove the back",
                "inside the", "power supply", "capacitor", "high voltage",
                "mains", "solder", "short", "bypass", "jumper", "bridge",
                "puncture", "crush", "heat the", "microwave", "oven"
            ]
            instruction_lower = step.instruction.lower()
            if any(kw in instruction_lower for kw in dangerous_keywords):
                errors.append(f"Step {step.step} contains potentially dangerous instruction")
                return False, errors

        if hasattr(result, "technician_required") and result.technician_required:
            if not result.technician_reason:
                errors.append("Technician required but no reason provided")

        return len(errors) == 0, errors


safety_service = SafetyService()