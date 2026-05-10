interface CanSubmitProfileFormArgs {
  hasUser: boolean;
  isSaving: boolean;
  isFormDirty: boolean;
  isEmailValid: boolean;
  isPhoneValid: boolean;
  isBioOverLimit: boolean;
}

export function canSubmitProfileForm({
  hasUser,
  isSaving,
  isFormDirty,
  isEmailValid,
  isPhoneValid,
  isBioOverLimit,
}: CanSubmitProfileFormArgs): boolean {
  return (
    hasUser &&
    !isSaving &&
    isFormDirty &&
    isEmailValid &&
    isPhoneValid &&
    !isBioOverLimit
  );
}
