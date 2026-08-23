from common.exceptions import BusinessRuleViolationError, PermissionDeniedError


class BenefitInactiveError(BusinessRuleViolationError):
    """Raised when attempting to grant or operate on an inactive benefit."""


class BenefitInheritanceError(BusinessRuleViolationError):
    """Raised when a unit tries to grant a benefit not available in its hierarchy."""


class BenefitScopeMismatchError(BusinessRuleViolationError):
    """Raised when the grant recipient (family vs member) does not match the benefit scope."""


class BenefitAlreadyGrantedError(BusinessRuleViolationError):
    """Raised when a family-scoped benefit has already been granted to the family."""


class BenefitProtectedError(BusinessRuleViolationError):
    """Raised when attempting to delete a benefit that has historical concessions."""


class BenefitEditNotAllowedError(PermissionDeniedError):
    """Raised when a child unit tries to edit an inherited benefit created by a parent unit."""
