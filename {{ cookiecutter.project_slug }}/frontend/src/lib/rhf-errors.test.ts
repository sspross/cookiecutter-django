import { describe, expect, it, vi } from "vitest";

import { applyApiErrorsToForm } from "./rhf-errors";

function makeForm() {
  return { setError: vi.fn() };
}

describe("applyApiErrorsToForm", () => {
  it("maps a per-field 422 to setError on that field", () => {
    const form = makeForm();
    const applied = applyApiErrorsToForm(form, {
      detail: [{ loc: ["body", "name"], msg: "This field is required.", type: "value_error" }],
    });
    expect(applied).toBe(true);
    expect(form.setError).toHaveBeenCalledWith("name", {
      type: "server",
      message: "This field is required.",
    });
  });

  it("uses dotted notation for nested fields", () => {
    const form = makeForm();
    applyApiErrorsToForm(form, {
      detail: [{ loc: ["body", "address", "zip"], msg: "Bad zip" }],
    });
    expect(form.setError).toHaveBeenCalledWith("address.zip", {
      type: "server",
      message: "Bad zip",
    });
  });

  it("falls back to root.serverError when there is no field path", () => {
    const form = makeForm();
    applyApiErrorsToForm(form, {
      detail: [{ loc: ["body"], msg: "Something is wrong" }],
    });
    expect(form.setError).toHaveBeenCalledWith("root.serverError", {
      type: "server",
      message: "Something is wrong",
    });
  });

  it("applies multiple errors in one call", () => {
    const form = makeForm();
    applyApiErrorsToForm(form, {
      detail: [
        { loc: ["body", "name"], msg: "Required" },
        { loc: ["body", "slug"], msg: "Invalid" },
      ],
    });
    expect(form.setError).toHaveBeenCalledTimes(2);
  });

  it("returns false and does nothing when error has no detail array", () => {
    const form = makeForm();
    expect(applyApiErrorsToForm(form, null)).toBe(false);
    expect(applyApiErrorsToForm(form, {})).toBe(false);
    expect(applyApiErrorsToForm(form, { detail: "oops" })).toBe(false);
    expect(applyApiErrorsToForm(form, "oops")).toBe(false);
    expect(form.setError).not.toHaveBeenCalled();
  });

  it("skips malformed detail entries instead of throwing", () => {
    const form = makeForm();
    const applied = applyApiErrorsToForm(form, {
      detail: [
        null,
        { loc: "not-an-array", msg: "x" },
        { loc: ["body", "name"], msg: 42 },
        { loc: ["body", "good"], msg: "ok" },
      ],
    });
    expect(applied).toBe(true);
    expect(form.setError).toHaveBeenCalledTimes(1);
    expect(form.setError).toHaveBeenCalledWith("good", {
      type: "server",
      message: "ok",
    });
  });
});
