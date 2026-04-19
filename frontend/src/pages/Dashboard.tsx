import React from "react";

export default function StreamlitPage() {
  return (
    <div style={{ width: "100%", height: "100vh" }}>
      <iframe
        src="http://localhost:8501"
        title="Streamlit Dashboard"
        style={{
          width: "100%",
          height: "100%",
          border: "none",
        }}
      />
    </div>
  );
}