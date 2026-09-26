import { describe, it, expect } from "vitest";
import {
  resolveReturnPath,
  isDashboardPending,
  resolvePostSaveRoute,
} from "./leadReturn";

describe("resolveReturnPath", () => {
  it("maps dashboard-pending to the dashboard", () => {
    expect(resolveReturnPath("dashboard-pending")).toBe("/dashboard");
  });

  it("maps pending-list to the filtered lead list", () => {
    expect(resolveReturnPath("pending-list")).toBe("/leads?followup=pending");
  });

  it("maps list to the lead list", () => {
    expect(resolveReturnPath("list")).toBe("/leads");
  });

  it("defaults unknown sources to /leads", () => {
    expect(resolveReturnPath("http://evil.example.com")).toBe("/leads");
    expect(resolveReturnPath("../../etc/passwd")).toBe("/leads");
  });

  it("defaults missing / empty / null sources to /leads", () => {
    expect(resolveReturnPath(undefined)).toBe("/leads");
    expect(resolveReturnPath(null)).toBe("/leads");
    expect(resolveReturnPath("")).toBe("/leads");
  });
});

describe("isDashboardPending", () => {
  it("is true only for the dashboard-pending source", () => {
    expect(isDashboardPending("dashboard-pending")).toBe(true);
    expect(isDashboardPending("pending-list")).toBe(false);
    expect(isDashboardPending("list")).toBe(false);
    expect(isDashboardPending(undefined)).toBe(false);
  });
});

describe("resolvePostSaveRoute", () => {
  it("returns to the dashboard from the dashboard-pending queue", () => {
    expect(resolvePostSaveRoute("dashboard-pending")).toBe("/dashboard");
  });

  it("returns to the filtered list from the pending-list queue", () => {
    expect(resolvePostSaveRoute("pending-list")).toBe("/leads?followup=pending");
  });

  it("stays on the detail page from the normal list", () => {
    expect(resolvePostSaveRoute("list")).toBeNull();
  });

  it("stays on the detail page for unknown / missing / empty sources", () => {
    expect(resolvePostSaveRoute("http://evil.example.com")).toBeNull();
    expect(resolvePostSaveRoute("../../etc/passwd")).toBeNull();
    expect(resolvePostSaveRoute(undefined)).toBeNull();
    expect(resolvePostSaveRoute(null)).toBeNull();
    expect(resolvePostSaveRoute("")).toBeNull();
  });
});
