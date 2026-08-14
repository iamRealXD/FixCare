import pytest

from app.services.safety_service import (
    safety_service,
    SafetyRiskCategory,
    RiskLevel,
)


class TestSafetyService:
    def test_safe_input_returns_safe(self):
        result = safety_service.screen_user_input(
            "My laptop won't turn on",
            "laptop",
        )
        assert result.safe is True
        assert result.risk_level == RiskLevel.SAFE
        assert result.detected_risks == []
        assert result.technician_required is False

    def test_swollen_battery_triggers_critical(self):
        result = safety_service.screen_user_input(
            "My phone has a swollen battery",
            "mobile",
        )
        assert result.safe is False
        assert result.risk_level == RiskLevel.CRITICAL
        assert SafetyRiskCategory.BATTERY_SWELLING in result.detected_risks
        assert result.technician_required is True
        assert result.escalation_message is not None

    def test_burning_smell_triggers_high(self):
        result = safety_service.screen_user_input(
            "There's a burning smell coming from my laptop",
            "laptop",
        )
        assert result.safe is False
        assert result.risk_level == RiskLevel.HIGH
        assert SafetyRiskCategory.BURNING_SMELL in result.detected_risks
        assert result.technician_required is True

    def test_smoke_triggers_critical(self):
        result = safety_service.screen_user_input(
            "Smoke is coming from my TV",
            "tv",
        )
        assert result.safe is False
        assert result.risk_level == RiskLevel.CRITICAL
        assert SafetyRiskCategory.SMOKE in result.detected_risks

    def test_sparks_triggers_critical(self):
        result = safety_service.screen_user_input(
            "I see sparks when I plug in my laptop",
            "laptop",
        )
        assert result.safe is False
        assert result.risk_level == RiskLevel.CRITICAL
        assert SafetyRiskCategory.SPARKS in result.detected_risks

    def test_electrical_shock_triggers_critical(self):
        result = safety_service.screen_user_input(
            "I got an electric shock from my phone charger",
            "mobile",
        )
        assert result.safe is False
        assert result.risk_level == RiskLevel.CRITICAL
        assert SafetyRiskCategory.ELECTRICAL_SHOCK in result.detected_risks

    def test_water_damage_triggers_high(self):
        result = safety_service.screen_user_input(
            "I spilled water on my laptop",
            "laptop",
        )
        assert result.safe is False
        assert result.risk_level >= RiskLevel.MODERATE
        assert SafetyRiskCategory.WATER_DAMAGE in result.detected_risks

    def test_tv_high_voltage_triggers_critical(self):
        result = safety_service.screen_user_input(
            "TV power supply capacitor issue",
            "tv",
        )
        assert result.safe is False
        assert result.risk_level == RiskLevel.CRITICAL
        assert result.technician_required is True

    def test_multiple_risks_uses_highest(self):
        result = safety_service.screen_user_input(
            "Smoke and burning smell from laptop",
            "laptop",
        )
        assert result.risk_level == RiskLevel.CRITICAL
        assert SafetyRiskCategory.SMOKE in result.detected_risks
        assert SafetyRiskCategory.BURNING_SMELL in result.detected_risks

    def test_validate_ai_response_rejects_high_risk_steps(self):
        from app.schemas.diagnosis import SafeStep, RiskLevel
        
        class MockResult:
            safe_steps = [
                SafeStep(step=1, instruction="Open the power supply", purpose="Test", risk=RiskLevel.HIGH)
            ]
            technician_required = False
        
        valid, errors = safety_service.validate_ai_response(MockResult())
        assert valid is False
        assert len(errors) > 0

    def test_validate_ai_response_rejects_dangerous_instructions(self):
        from app.schemas.diagnosis import SafeStep, RiskLevel
        
        class MockResult:
            safe_steps = [
                SafeStep(step=1, instruction="Disassemble the TV and check capacitors", purpose="Test", risk=RiskLevel.SAFE)
            ]
            technician_required = False
        
        valid, errors = safety_service.validate_ai_response(MockResult())
        assert valid is False
        assert len(errors) > 0

    def test_validate_ai_response_accepts_safe_steps(self):
        from app.schemas.diagnosis import SafeStep, RiskLevel
        
        class MockResult:
            safe_steps = [
                SafeStep(step=1, instruction="Restart the device", purpose="Test", risk=RiskLevel.SAFE),
                SafeStep(step=2, instruction="Check cables", purpose="Test", risk=RiskLevel.LOW),
            ]
            technician_required = False
        
        valid, errors = safety_service.validate_ai_response(MockResult())
        assert valid is True
        assert len(errors) == 0

    def test_validate_ai_response_requires_technician_reason(self):
        from app.schemas.diagnosis import SafeStep, RiskLevel
        
        class MockResult:
            safe_steps = [
                SafeStep(step=1, instruction="Restart the device", purpose="Test", risk=RiskLevel.SAFE)
            ]
            technician_required = True
            technician_reason = None
        
        valid, errors = safety_service.validate_ai_response(MockResult())
        assert valid is False
        assert any("reason" in e.lower() for e in errors)