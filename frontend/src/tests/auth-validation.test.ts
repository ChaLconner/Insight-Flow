import { describe, it, expect } from 'vitest';
import { loginSchema, registerSchema } from '@/lib/validations/auth';

describe('Auth Validation Schemas', () => {
  it('validates login schema correctly', () => {
    expect(loginSchema.safeParse({ email: 'invalid', password: '' }).success).toBe(false);
    expect(loginSchema.safeParse({ email: 'user@example.com', password: 'password123' }).success).toBe(true);
  });

  it('validates register schema password matching and terms requirement', () => {
    const validData = {
      fullName: 'John Doe',
      email: 'john@example.com',
      password: 'password123',
      confirmPassword: 'password123',
      terms: true,
    };
    expect(registerSchema.safeParse(validData).success).toBe(true);

    const mismatchedPass = { ...validData, confirmPassword: 'different' };
    const resMismatched = registerSchema.safeParse(mismatchedPass);
    expect(resMismatched.success).toBe(false);

    const noTerms = { ...validData, terms: false };
    const resNoTerms = registerSchema.safeParse(noTerms);
    expect(resNoTerms.success).toBe(false);
  });
});
