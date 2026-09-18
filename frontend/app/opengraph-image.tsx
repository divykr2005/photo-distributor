import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "SnapTracer — private event photo matching";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          alignItems: "center",
          background: "linear-gradient(135deg, #09090b 0%, #18181b 55%, #312e81 100%)",
          color: "white",
          display: "flex",
          height: "100%",
          justifyContent: "center",
          width: "100%",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", maxWidth: 920 }}>
          <div style={{ color: "#a5b4fc", display: "flex", fontSize: 28, letterSpacing: 5 }}>
            SNAPTRACER
          </div>
          <div style={{ display: "flex", fontSize: 76, fontWeight: 700, lineHeight: 1.08, marginTop: 24 }}>
            Find every photo you appear in.
          </div>
          <div style={{ color: "#d4d4d8", display: "flex", fontSize: 32, marginTop: 32 }}>
            Private AI photo matching for events.
          </div>
        </div>
      </div>
    ),
    size,
  );
}
