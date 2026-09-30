const SLOGAN = "사용자 여러분의 Trip 경험을 공유해주세요! (Share Your Experience)";
const COPY = "직접 다녀온 숨은 맛집과 감성 여행지를 제보해 주시면, 검토 후 공식 매거진으로 발행해 드립니다.";
const CTA = "매거진 발행 요청하기";

export default function MagazineRequestCta({ onRequest }) {
  return (
    <section className="magazine-cta" aria-labelledby="magazine-cta-title">
      <h2 id="magazine-cta-title">{SLOGAN}</h2>
      <p>{COPY}</p>
      <button type="button" className="magazine-cta-button" onClick={onRequest}>
        {CTA}
      </button>
    </section>
  );
}
