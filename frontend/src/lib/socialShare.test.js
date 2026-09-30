import { describe, expect, it } from "vitest";
import { adsTxtBody, adsTxtLine, normalizePublisherId } from "./adsTxt";
import { absoluteShareUrl, kakaoFeedObject, shareCaption, xShareUrl } from "./socialShare";

describe("ads.txt publisher line", () => {
  it("formats a publisher id and ignores an empty value", () => {
    expect(normalizePublisherId("ca-pub-1234567890123456")).toBe("pub-1234567890123456");
    expect(adsTxtLine("pub-1234567890123456")).toBe(
      "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0",
    );
    expect(adsTxtBody("")).toContain("ads.txt disabled");
    expect(adsTxtBody("not-an-id")).toContain("ads.txt disabled");
  });
});

describe("social share payloads", () => {
  it("builds an absolute page url, an X intent, and a Kakao feed", () => {
    expect(absoluteShareUrl("/guide/kyoto_guide.md")).toBe(
      "https://www.bluelogtrip.com/guide/kyoto_guide.md",
    );
    expect(xShareUrl({ title: "Kyoto", url: "https://www.bluelogtrip.com/guide/kyoto_guide.md" })).toContain(
      "twitter.com/intent/tweet",
    );
    expect(shareCaption({ title: "Kyoto", description: "A walk", url: "https://www.bluelogtrip.com/guide/kyoto_guide.md" }))
      .toContain("Kyoto");
    const feed = kakaoFeedObject({
      title: "Kyoto",
      description: "A walk",
      imageUrl: "https://images.example/kyoto.jpg",
      url: "https://www.bluelogtrip.com/guide/kyoto_guide.md",
    });
    expect(feed.objectType).toBe("feed");
    expect(feed.content.imageUrl).toBe("https://images.example/kyoto.jpg");
    expect(feed.content.link.webUrl).toContain("/guide/kyoto_guide.md");
  });
});
