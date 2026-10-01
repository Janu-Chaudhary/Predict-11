import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useLoaderVisibility } from "./use-loader-visibility";

const T = { showDelay: 800, minVisible: 600, slowAfter: 8000 };

describe("useLoaderVisibility (§7.2 timing rules)", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  const setup = (pending = true) =>
    renderHook(({ p }) => useLoaderVisibility(p, T), { initialProps: { p: pending } });

  it("shows nothing for waits under the 800 ms delay", () => {
    const { result, rerender } = setup();
    act(() => vi.advanceTimersByTime(799));
    expect(result.current.visible).toBe(false);
    rerender({ p: false });
    act(() => vi.advanceTimersByTime(2000));
    expect(result.current.visible).toBe(false);
  });

  it("appears at 800 ms", () => {
    const { result } = setup();
    act(() => vi.advanceTimersByTime(800));
    expect(result.current.visible).toBe(true);
  });

  it("stays visible at least 600 ms once shown, even if loading ends right away", () => {
    const { result, rerender } = setup();
    act(() => vi.advanceTimersByTime(900)); // shown at 800, 100 ms visible so far
    rerender({ p: false });
    act(() => vi.advanceTimersByTime(499));
    expect(result.current.visible).toBe(true);
    act(() => vi.advanceTimersByTime(1));
    expect(result.current.visible).toBe(false);
  });

  it("hides immediately if it has already been visible for 600 ms", () => {
    const { result, rerender } = setup();
    act(() => vi.advanceTimersByTime(800 + 700));
    rerender({ p: false });
    act(() => vi.advanceTimersByTime(0));
    expect(result.current.visible).toBe(false);
  });

  it("flags slow waits after 8 s and resets when done", () => {
    const { result, rerender } = setup();
    act(() => vi.advanceTimersByTime(7999));
    expect(result.current.slow).toBe(false);
    act(() => vi.advanceTimersByTime(1));
    expect(result.current.slow).toBe(true);
    rerender({ p: false });
    act(() => vi.advanceTimersByTime(0));
    expect(result.current).toEqual({ visible: false, slow: false });
  });

  it("restarts the delay on a new pending period", () => {
    const { result, rerender } = setup();
    act(() => vi.advanceTimersByTime(1000));
    rerender({ p: false });
    act(() => vi.advanceTimersByTime(600));
    expect(result.current.visible).toBe(false);
    rerender({ p: true });
    act(() => vi.advanceTimersByTime(500));
    expect(result.current.visible).toBe(false);
    act(() => vi.advanceTimersByTime(300));
    expect(result.current.visible).toBe(true);
  });
});
