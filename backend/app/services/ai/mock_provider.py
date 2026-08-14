import asyncio
import json
import random
from uuid import UUID
from typing import Any

from app.services.ai.base import AIProvider, AIProviderMetadata
from app.schemas.diagnosis import (
    DiagnosisRequest,
    DiagnosisResultResponse,
    PossibleCause,
    SafeStep,
    RiskItem,
    FollowUpQuestion,
    RiskLevel,
    DeviceCategory,
    DiagnosisSeverity,
)
from app.core.config import get_settings


class MockAIProvider(AIProvider):
    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-diagnosis-v1"

    async def diagnose(
        self,
        request: DiagnosisRequest,
        diagnosis_id: UUID | None = None,
    ) -> tuple[DiagnosisResultResponse, AIProviderMetadata]:
        await asyncio.sleep(0.5)

        category = request.device_category.value
        problem = request.problem_description.lower()

        possible_causes = self._generate_causes(category, problem)
        safe_steps = self._generate_steps(category, problem)
        risks = self._generate_risks(category, problem)
        follow_up_questions = self._generate_followups(category, problem)
        technician_required, technician_reason = self._check_technician(category, problem)

        result = DiagnosisResultResponse(
            device={
                "category": category,
                "brand": request.brand,
                "model": request.model,
            },
            problem={
                "summary": request.problem_description[:200],
                "severity": self._assess_severity(problem).value,
            },
            possible_causes=possible_causes,
            safe_steps=safe_steps,
            risks=risks,
            technician_required=technician_required,
            technician_reason=technician_reason,
            follow_up_questions=follow_up_questions,
            disclaimer=(
                "This is troubleshooting guidance, not a confirmed hardware diagnosis. "
                "FixCare provides probabilistic troubleshooting assistance only. "
                "For safety-critical issues, always consult a qualified technician."
            ),
        )

        metadata = AIProviderMetadata(
            provider=self.provider_name,
            model=self.model_name,
            prompt_version="mock-v1",
            latency_ms=random.randint(300, 800),
            input_tokens=random.randint(100, 500),
            output_tokens=random.randint(200, 800),
            estimated_cost=0.0,
            success=True,
        )

        return result, metadata

    async def health_check(self) -> bool:
        return True

    def _assess_severity(self, problem: str) -> DiagnosisSeverity:
        critical_keywords = ["smoke", "fire", "spark", "burning", "shock", "explos", "swollen"]
        high_keywords = ["won't turn on", "black screen", "no power", "dead", "overheat"]
        
        if any(kw in problem for kw in critical_keywords):
            return DiagnosisSeverity.CRITICAL
        if any(kw in problem for kw in high_keywords):
            return DiagnosisSeverity.HIGH
        return DiagnosisSeverity.MEDIUM

    def _generate_causes(self, category: str, problem: str) -> list[PossibleCause]:
        causes_map = {
            "mobile": [
                ("Battery or charging issue", 0.8, "high"),
                ("Screen or display connection problem", 0.65, "medium"),
                ("Software crash or OS issue", 0.55, "possible"),
                ("Water damage", 0.3, "possible"),
                ("Motherboard failure", 0.2, "unlikely"),
            ],
            "laptop": [
                ("Power adapter or battery issue", 0.75, "high"),
                ("Display or GPU problem", 0.6, "medium"),
                ("RAM or motherboard issue", 0.45, "possible"),
                ("Overheating / thermal throttling", 0.4, "possible"),
                ("SSD/HDD failure", 0.3, "possible"),
            ],
            "tv": [
                ("Power supply or mainboard issue", 0.7, "high"),
                ("Backlight or panel failure", 0.55, "medium"),
                ("HDMI / input source problem", 0.5, "medium"),
                ("Firmware / software issue", 0.4, "possible"),
                ("Capacitor degradation", 0.25, "unlikely"),
            ],
        }

        causes = causes_map.get(category, causes_map["laptop"])
        return [
            PossibleCause(cause=c, confidence=conf, likelihood=lik)
            for c, conf, lik in causes
        ]

    def _generate_steps(self, category: str, problem: str) -> list[SafeStep]:
        steps_map = {
            "mobile": [
                SafeStep(
                    step=1,
                    instruction="Force restart the device by holding power + volume down for 15-20 seconds.",
                    purpose="Clears temporary software glitches and resets the power state.",
                    risk=RiskLevel.SAFE,
                ),
                SafeStep(
                    step=2,
                    instruction="Connect to a known-good charger and cable for at least 30 minutes.",
                    purpose="Rules out a depleted battery or faulty charging accessory.",
                    risk=RiskLevel.SAFE,
                ),
                SafeStep(
                    step=3,
                    instruction="Check for physical damage, liquid indicators, or swollen battery.",
                    purpose="Identifies hardware damage that requires professional repair.",
                    risk=RiskLevel.SAFE,
                ),
                SafeStep(
                    step=4,
                    instruction="If accessible, try booting into safe mode or recovery mode.",
                    purpose="Determines if third-party apps are causing the issue.",
                    risk=RiskLevel.LOW,
                ),
            ],
            "laptop": [
                SafeStep(
                    step=1,
                    instruction="Disconnect all peripherals (USB devices, external monitors, dock).",
                    purpose="Rules out peripheral-related power or startup issues.",
                    risk=RiskLevel.SAFE,
                ),
                SafeStep(
                    step=2,
                    instruction="Connect the original charger directly to a wall outlet (not a power strip).",
                    purpose="Ensures adequate power delivery and rules out power strip issues.",
                    risk=RiskLevel.SAFE,
                ),
                SafeStep(
                    step=3,
                    instruction="Hold the power button for 30 seconds with charger disconnected, then reconnect and try powering on.",
                    purpose="Performs a hard reset / clears residual power (flea power).",
                    risk=RiskLevel.SAFE,
                ),
                SafeStep(
                    step=4,
                    instruction="Check for LED indicators, fan noise, or keyboard backlight when pressing power.",
                    purpose="Determines if power is reaching the system board.",
                    risk=RiskLevel.SAFE,
                ),
                SafeStep(
                    step=5,
                    instruction="If external monitor available, connect it to test if display is the issue.",
                    purpose="Isolates whether the problem is the screen or the GPU/system.",
                    risk=RiskLevel.LOW,
                ),
            ],
            "tv": [
                SafeStep(
                    step=1,
                    instruction="Unplug the TV from the wall outlet, wait 60 seconds, then plug back in.",
                    purpose="Performs a full power cycle to clear temporary faults.",
                    risk=RiskLevel.SAFE,
                ),
                SafeStep(
                    step=2,
                    instruction="Check the power outlet with another device (lamp, phone charger).",
                    purpose="Rules out a faulty wall outlet or power strip.",
                    risk=RiskLevel.SAFE,
                ),
                SafeStep(
                    step=3,
                    instruction="Try a different HDMI cable and input source.",
                    purpose="Rules out cable or source device issues.",
                    risk=RiskLevel.SAFE,
                ),
                SafeStep(
                    step=4,
                    instruction="Check for standby/power LED behavior (blinking patterns).",
                    purpose="Many TVs indicate error codes via LED blink patterns.",
                    risk=RiskLevel.SAFE,
                ),
                SafeStep(
                    step=5,
                    instruction="If under warranty, contact manufacturer support before further troubleshooting.",
                    purpose="Avoids voiding warranty on sealed units.",
                    risk=RiskLevel.LOW,
                ),
            ],
        }

        return steps_map.get(category, steps_map["laptop"])

    def _generate_risks(self, category: str, problem: str) -> list[RiskItem]:
        risks = []

        critical_keywords = ["smoke", "fire", "spark", "burning", "shock", "explos", "swollen", "bulg"]
        if any(kw in problem for kw in critical_keywords):
            risks.append(RiskItem(
                risk=RiskLevel.CRITICAL,
                description="Signs of dangerous electrical or battery failure detected.",
                action="STOP using the device immediately. Unplug from power. Do not attempt further troubleshooting. Contact a qualified technician or emergency services if there is active danger."
            ))

        high_keywords = ["water", "liquid", "spill", "dropped", "cracked"]
        if any(kw in problem for kw in high_keywords):
            risks.append(RiskItem(
                risk=RiskLevel.HIGH,
                description="Physical damage or liquid exposure suspected.",
                action="Do not power on the device. Internal corrosion or short circuits may worsen with power. Professional assessment required."
            ))

        if category == "tv":
            risks.append(RiskItem(
                risk=RiskLevel.HIGH,
                description="TVs contain high-voltage components that can retain dangerous charge even when unplugged.",
                action="Never open a TV casing. Internal capacitors can hold lethal voltage. All internal repairs must be performed by qualified technicians."
            ))

        if not risks:
            risks.append(RiskItem(
                risk=RiskLevel.SAFE,
                description="Standard troubleshooting carries minimal risk when following provided steps.",
                action="Follow steps in order. Stop if you encounter unexpected behavior, unusual smells, sounds, or heat."
            ))

        return risks

    def _generate_followups(self, category: str, problem: str) -> list[FollowUpQuestion]:
        questions_map = {
            "mobile": [
                FollowUpQuestion(
                    question="When you press the power button, what happens?",
                    options=["Nothing at all", "Vibration but no screen", "Logo appears then shuts off", "Screen flickers", "Error message"],
                ),
                FollowUpQuestion(
                    question="Has the device been exposed to liquid or dropped recently?",
                    options=["Yes - liquid", "Yes - dropped", "Both", "No / unsure"],
                ),
            ],
            "laptop": [
                FollowUpQuestion(
                    question="When you press the power button, what happens?",
                    options=["No lights or sound", "Power LED turns on", "Fan spins briefly", "Keyboard lights up", "External monitor works"],
                ),
                FollowUpQuestion(
                    question="Does the laptop work when connected to an external monitor?",
                    options=["Yes - external works", "No - external also blank", "Haven't tried", "No external monitor available"],
                ),
            ],
            "tv": [
                FollowUpQuestion(
                    question="What is the standby/power LED doing?",
                    options=["Off completely", "Solid on", "Blinking (count blinks)", "Normal color but no picture"],
                ),
                FollowUpQuestion(
                    question="Do you hear any sound from the TV?",
                    options=["Normal sound", "Buzzing/humming", "Clicking", "No sound at all"],
                ),
            ],
        }

        return questions_map.get(category, questions_map["laptop"])

    def _check_technician(self, category: str, problem: str) -> tuple[bool, str | None]:
        critical_keywords = ["smoke", "fire", "spark", "burning", "shock", "explos", "swollen", "bulg"]
        if any(kw in problem for kw in critical_keywords):
            return True, "Dangerous condition detected. Immediate professional service required."

        if category == "tv" and any(kw in problem for kw in ["power supply", "capacitor", "mainboard", "high voltage"]):
            return True, "TV internal power components involve lethal voltages. Only qualified technicians should service."

        return False, None