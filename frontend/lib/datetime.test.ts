import { describe, it, expect } from "vitest";
import { formatSystemTime, formatNextFollowup } from "./datetime";

describe("formatSystemTime", () => {
  it("converts a space-separated UTC timestamp to Beijing time", () => {
    // Backend stores UTC wall clock "YYYY-MM-DD HH:MM:SS".
    expect(formatSystemTime("2026-08-24 16:05:38")).toBe("2026-08-25 00:05:38");
  });

  it("converts an ISO UTC timestamp (T + Z) to Beijing time", () => {
    expect(formatSystemTime("2026-08-24T16:05:38Z")).toBe("2026-08-25 00:05:38");
  });

  it("converts an ISO UTC timestamp (T, no Z) to Beijing time", () => {
    expect(formatSystemTime("2026-08-24T16:05:38")).toBe("2026-08-25 00:05:38");
  });

  it("rolls the day forward across midnight", () => {
    expect(formatSystemTime("2026-08-24 23:00:00")).toBe("2026-08-25 07:00:00");
  });

  it("returns - for empty values", () => {
    expect(formatSystemTime(null)).toBe("-");
    expect(formatSystemTime(undefined)).toBe("-");
    expect(formatSystemTime("")).toBe("-");
  });

  it("returns the original string when it cannot be parsed", () => {
    expect(formatSystemTime("not-a-date")).toBe("not-a-date");
  });
});

describe("formatNextFollowup", () => {
  it("redraws a datetime-local value without any timezone shift", () => {
    // The user picked 15:30 Beijing time; it must stay 15:30, never ±8h.
    expect(formatNextFollowup("2026-08-25T15:30")).toBe("2026-08-25 15:30");
  });

  it("normalizes a space-separated value to HH:MM", () => {
    expect(formatNextFollowup("2026-08-25 15:30:00")).toBe("2026-08-25 15:30");
  });

  it("keeps a minutes-only value unchanged", () => {
    expect(formatNextFollowup("2026-08-25 15:30")).toBe("2026-08-25 15:30");
  });

  it("does not drift across midnight or day boundaries", () => {
    expect(formatNextFollowup("2026-08-24T23:55")).toBe("2026-08-24 23:55");
  });

  it("returns - for empty values", () => {
    expect(formatNextFollowup(null)).toBe("-");
    expect(formatNextFollowup(undefined)).toBe("-");
    expect(formatNextFollowup("")).toBe("-");
  });
});
