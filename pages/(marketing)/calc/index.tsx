import React, { useState } from "react";

export default function Calc() {

  const [formula, setFormula] = useState("");
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);

  async function calculate() {

    if (!formula) return;

    setLoading(true);
    setResult("");

    try {

      const res = await fetch("/api/calc", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          formula: formula
        })
      });

      const data = await res.json();

      if (data.status === "success") {
        setResult(data.result);
      } else {
        setResult("Error: " + data.message);
      }

    } catch (err) {
      setResult("Server Error");
    }

    setLoading(false);
  }

  return (
    <div>

      <h1>Calculator</h1>

      <p>Enter any math formula</p>

      <input
        type="text"
        value={formula}
        onChange={(e) => setFormula(e.target.value)}
        placeholder="5+10*2"
        style={{
          padding: "10px",
          width: "250px",
          marginRight: "10px"
        }}
      />

      <button
        onClick={calculate}
        style={{
          padding: "10px 20px",
          cursor: "pointer"
        }}
      >
        {loading ? "Calculating..." : "Calculate"}
      </button>

      <div style={{ marginTop: "20px" }}>
        <h2>Result: {result}</h2>
      </div>

    </div>
  );
}