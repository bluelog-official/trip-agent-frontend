import { describe, expect, it } from "vitest";
import { consumeAuthReturn, readUserSession, rememberAuthReturn, storeUserSession } from "./session";

describe("user session storage", () => {
  it("keeps a bearer session and drops an empty one", () => {
    const storage = new Map();
    const memory = {
      getItem: (key) => (storage.has(key) ? storage.get(key) : null),
      setItem: (key, value) => storage.set(key, value),
      removeItem: (key) => storage.delete(key),
    };
    expect(storeUserSession({ token: "", email: "a@b.c" }, memory)).toBeNull();
    const saved = storeUserSession(
      { token: "abc.def", email: "hana@example.com", auth_provider: "kakao", user_id: 4, points_balance: 150 },
      memory,
    );
    expect(saved.provider).toBe("kakao");
    expect(readUserSession(memory).pointsBalance).toBe(150);
    rememberAuthReturn("/magazine-request", memory);
    expect(consumeAuthReturn(memory)).toBe("/magazine-request");
    expect(consumeAuthReturn(memory)).toBe("");
  });
});
