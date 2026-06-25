/*
 * generate_pptx.js
 * ================
 * Generates the FraudShield AI presentation as a real .pptx using PptxGenJS.
 *
 * Design: premium fintech / C-level consulting style.
 *   Theme  -> dark navy, electric blue, white, light gray.
 *   Slides -> short bullets only; the detail lives in SPEAKER NOTES so the
 *             presenter sees it in Presenter View while the audience sees a
 *             clean slide.
 *
 * Every slide uses slide.addNotes(...) with notes split by speaker:
 *   Krishna Mathur    -> intro, business problem, dashboard, conclusion
 *   Yash Petkar       -> dataset, preprocessing, feature engineering
 *   Atharva Soundankar-> LSTM architecture, model training, evaluation
 *   4th member (blank)-> limitations, ethics, future scope
 *
 * Run:
 *   npm install
 *   node presentation/generate_pptx.js
 */

const path = require("path");
const pptxgen = require("pptxgenjs");

const pptx = new pptxgen();
pptx.defineLayout({ name: "FS", width: 13.333, height: 7.5 });
pptx.layout = "FS";
pptx.author = "Krishna Mathur, Yash Petkar, Atharva Soundankar";
pptx.company = "MAIB Sept 25 - Term 3";
pptx.title = "FraudShield AI: Payment Fraud Sequence Detection using LSTM/RNN";

/* ---------------------------------------------------------------- palette */
const C = {
  navy: "0B1F3A",
  navy2: "12294D",
  blue: "2563EB",
  blueLt: "3B82F6",
  cyan: "38BDF8",
  white: "FFFFFF",
  gray: "94A3B8",
  grayLt: "E2E8F0",
  green: "16A34A",
  amber: "F59E0B",
  red: "DC2626",
  slate: "1E293B",
};

const FONT = "Arial";
const W = 13.333;
const H = 7.5;

/* ------------------------------------------------------------ master slide */
pptx.defineSlideMaster({
  title: "FS_MASTER",
  background: { color: C.navy },
  objects: [
    // thin electric-blue accent bar along the top
    { rect: { x: 0, y: 0, w: W, h: 0.12, fill: { color: C.blue } } },
    // footer brand + page area
    { rect: { x: 0, y: H - 0.42, w: W, h: 0.42, fill: { color: C.navy2 } } },
    {
      text: {
        text: "FraudShield AI  ·  Payment Fraud Sequence Detection (LSTM/RNN)",
        options: {
          x: 0.4, y: H - 0.42, w: 9, h: 0.42, fontFace: FONT,
          fontSize: 9, color: C.gray, align: "left", valign: "middle",
        },
      },
    },
    {
      text: {
        text: "MAIB Sept 25 · Term 3",
        options: {
          x: W - 3.4, y: H - 0.42, w: 3.0, h: 0.42, fontFace: FONT,
          fontSize: 9, color: C.gray, align: "right", valign: "middle",
        },
      },
    },
  ],
});

/* ----------------------------------------------------------- helper layout */
function newSlide() {
  return pptx.addSlide({ masterName: "FS_MASTER" });
}

// Standard title block for a content slide.
function addTitle(slide, kicker, title) {
  slide.addText(kicker.toUpperCase(), {
    x: 0.55, y: 0.42, w: 11.5, h: 0.3, fontFace: FONT, fontSize: 12,
    color: C.cyan, charSpacing: 2, bold: true,
  });
  slide.addText(title, {
    x: 0.5, y: 0.72, w: 12.3, h: 0.9, fontFace: FONT, fontSize: 30,
    color: C.white, bold: true,
  });
  // small underline accent
  slide.addShape(pptx.ShapeType.rect, {
    x: 0.55, y: 1.6, w: 1.1, h: 0.05, fill: { color: C.blue },
  });
}

// Bullet list helper (short bullets only).
function addBullets(slide, items, opts = {}) {
  const textObjs = items.map((t) => ({
    text: t,
    options: { bullet: { code: "2022", indent: 18 }, color: opts.color || C.grayLt,
      fontSize: opts.fontSize || 18, paraSpaceAfter: 10 },
  }));
  slide.addText(textObjs, {
    x: opts.x || 0.7, y: opts.y || 2.0, w: opts.w || 6.0, h: opts.h || 4.6,
    fontFace: FONT, valign: "top",
  });
}

// A rounded "card" with a heading and body — used for visuals/mockups.
function addCard(slide, x, y, w, h, heading, body, accent) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: C.navy2 }, line: { color: accent || C.blue, width: 1 },
    shadow: { type: "outer", color: "000000", opacity: 0.35, blur: 6, offset: 2, angle: 90 },
  });
  slide.addShape(pptx.ShapeType.rect, { x, y, w: 0.08, h, fill: { color: accent || C.blue } });
  slide.addText(heading, {
    x: x + 0.2, y: y + 0.12, w: w - 0.3, h: 0.4, fontFace: FONT,
    fontSize: 14, bold: true, color: C.white,
  });
  if (body) {
    slide.addText(body, {
      x: x + 0.2, y: y + 0.5, w: w - 0.35, h: h - 0.6, fontFace: FONT,
      fontSize: 12, color: C.grayLt, valign: "top",
    });
  }
}

// A pipeline of arrow-connected boxes (used for architecture slides).
function addFlow(slide, steps, y, opts = {}) {
  const startX = opts.x || 0.5;
  const totalW = opts.w || 12.3;
  const boxH = opts.h || 0.85;
  const gap = 0.25;
  const boxW = (totalW - gap * (steps.length - 1)) / steps.length;
  steps.forEach((s, i) => {
    const x = startX + i * (boxW + gap);
    const color = s.color || C.blue;
    slide.addShape(pptx.ShapeType.roundRect, {
      x, y, w: boxW, h: boxH, rectRadius: 0.06,
      fill: { color: C.navy2 }, line: { color, width: 1.25 },
    });
    slide.addText(s.label, {
      x: x + 0.05, y, w: boxW - 0.1, h: boxH, fontFace: FONT, fontSize: 11.5,
      color: C.white, align: "center", valign: "middle", bold: true,
    });
    if (i < steps.length - 1) {
      slide.addText("➔", {
        x: x + boxW - 0.02, y, w: gap + 0.04, h: boxH, fontFace: FONT,
        fontSize: 16, color: C.cyan, align: "center", valign: "middle",
      });
    }
  });
}

// Notes builder: per-speaker blocks for Presenter View.
function notes(parts) {
  // parts = [{who, text}, ...]
  return parts
    .map((p) => `[${p.who}]\n${p.text}`)
    .join("\n\n");
}

/* ====================================================================== *
 *  SLIDE 1 — TITLE
 * ====================================================================== */
{
  const s = newSlide();
  // big brand
  s.addShape(pptx.ShapeType.roundRect, {
    x: 0.6, y: 1.5, w: 1.2, h: 1.2, rectRadius: 0.12,
    fill: { color: C.blue }, line: { color: C.cyan, width: 1 },
  });
  s.addText("🛡", { x: 0.6, y: 1.5, w: 1.2, h: 1.2, fontSize: 40,
    align: "center", valign: "middle", color: C.white });

  s.addText("FraudShield AI", {
    x: 2.0, y: 1.55, w: 10.5, h: 0.9, fontFace: FONT, fontSize: 46,
    bold: true, color: C.white,
  });
  s.addText("Payment Fraud Sequence Detection using LSTM / RNN", {
    x: 2.0, y: 2.45, w: 10.7, h: 0.6, fontFace: FONT, fontSize: 22, color: C.cyan,
  });

  s.addShape(pptx.ShapeType.rect, { x: 0.6, y: 3.5, w: 4.2, h: 0.04, fill: { color: C.blue } });

  s.addText("Deep Learning Project  —  MAIB Sept 25 · Term 3", {
    x: 0.6, y: 3.7, w: 11, h: 0.4, fontFace: FONT, fontSize: 16, color: C.grayLt,
  });

  s.addText(
    [
      { text: "Group members:  ", options: { bold: true, color: C.white } },
      { text: "Krishna Mathur  ·  Yash Petkar  ·  Atharva Soundankar  ·  __________",
        options: { color: C.grayLt } },
    ],
    { x: 0.6, y: 4.3, w: 12, h: 0.5, fontFace: FONT, fontSize: 16 }
  );

  // three quiet value chips
  const chips = ["Sequence-aware fraud detection", "Risk score → business action", "Premium analyst dashboard"];
  chips.forEach((t, i) => {
    addCard(s, 0.6 + i * 4.1, 5.2, 3.8, 1.0, t, "", C.cyan);
  });

  s.addNotes(notes([
    { who: "Krishna Mathur", text:
      "Good morning everyone. We are Team FraudShield AI. Our project is about detecting payment fraud using deep learning. The key idea is simple: instead of judging one transaction alone, we look at a customer's recent sequence of transactions and decide if the next payment is fraud. I will introduce the problem and the business value, Yash will cover the data and features, Atharva will explain the LSTM model and how we evaluate it, and our fourth member will cover limitations, ethics and future scope. The whole presentation will take about 12 minutes. Let's begin." },
  ]));
}

/* ====================================================================== *
 *  SLIDE 2 — EXECUTIVE SUMMARY
 * ====================================================================== */
{
  const s = newSlide();
  addTitle(s, "Executive Summary", "What FraudShield AI does, in three points");
  addCard(s, 0.6, 2.1, 3.9, 3.6, "1 · Behaviour, not a single payment",
    "We detect fraud from the SEQUENCE of a customer's transactions, capturing how behaviour changes over time.", C.blueLt);
  addCard(s, 4.7, 2.1, 3.9, 3.6, "2 · LSTM learns the patterns",
    "An LSTM network reads the recent history and learns the suspicious payment patterns that simple rules miss.", C.cyan);
  addCard(s, 8.8, 2.1, 3.9, 3.6, "3 · Score → business action",
    "Every transaction gets a fraud probability mapped to a clear action: Approve, Review/OTP, or Block.", C.green);

  s.addNotes(notes([
    { who: "Krishna Mathur", text:
      "Here is our project in three business sentences. First, we look at customer behaviour over time, not just one isolated payment. Second, we use an LSTM, a type of neural network with memory, to learn what suspicious payment patterns look like. Third, and most importantly for the business, every transaction receives a fraud risk score that maps to a clear action: approve it, send it for manual review or one-time-password, or block it and alert the fraud team. So the output is not just a number — it is a decision the bank can act on immediately." },
  ]));
}

/* ====================================================================== *
 *  SLIDE 3 — BUSINESS PROBLEM
 * ====================================================================== */
{
  const s = newSlide();
  addTitle(s, "Business Problem", "Digital payment fraud is fast and hides in behaviour");
  addBullets(s, [
    "Sudden large transfers out of an account",
    "Rapid cash-outs right after a transfer",
    "Balance draining to zero in minutes",
    "Suspicious sequences of transactions",
    "High cost of manual fraud investigation",
  ], { y: 2.1, w: 6.2 });

  addCard(s, 7.2, 2.1, 5.5, 1.6, "The pattern that hurts",
    "100  →  120  →  9,000  →  9,500  →  balance 0\nA huge spike that empties the account.", C.red);
  addCard(s, 7.2, 3.85, 5.5, 1.85, "Why it is hard",
    "Fraud is rare, fast, and looks normal one row at a time. Investigators cannot manually check every payment.", C.amber);

  s.addNotes(notes([
    { who: "Krishna Mathur", text:
      "Let's talk about the real problem. Digital payments happen in seconds, and fraudsters exploit that speed. The typical attack looks like this: an account behaves normally with small amounts, then suddenly there is a very large transfer, followed by a quick cash-out, and the balance is drained to zero. By the time a human notices, the money is gone. On top of that, manually investigating every flagged payment is extremely expensive. So banks need a system that can spot these suspicious sequences automatically and in real time. That is exactly the gap FraudShield AI fills." },
  ]));
}

/* ====================================================================== *
 *  SLIDE 4 — WHY IT MATTERS
 * ====================================================================== */
{
  const s = newSlide();
  addTitle(s, "Why Fraud Detection Matters", "The business impact of getting this wrong");
  const items = [
    ["💸 Financial loss", "Direct money lost on every undetected fraud."],
    ["🤝 Customer trust", "Victims lose confidence and leave the bank."],
    ["⚖️ Regulatory risk", "Fines and compliance pressure from regulators."],
    ["🧰 Operational workload", "Analysts overloaded with manual reviews."],
    ["📉 Reputation damage", "Public fraud cases harm the brand."],
  ];
  items.forEach((it, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    addCard(s, 0.6 + col * 4.15, 2.1 + row * 1.75, 3.9, 1.6, it[0], it[1],
      [C.blueLt, C.cyan, C.amber, C.green, C.red][i]);
  });

  s.addNotes(notes([
    { who: "Krishna Mathur", text:
      "Why does this matter so much? There are five business impacts. One, direct financial loss — every missed fraud is money gone. Two, customer trust — a customer who is defrauded often leaves the bank for good. Three, regulatory risk — banks face fines if they fail to control fraud. Four, operational workload — without smart prioritisation, analysts drown in alerts. And five, reputation damage — a public fraud story can hurt the brand for years. A good detection system protects all five at once, which is why this is a board-level priority, not just a technical project." },
  ]));
}

/* ====================================================================== *
 *  SLIDE 5 — WHY RULES ARE NOT ENOUGH
 * ====================================================================== */
{
  const s = newSlide();
  addTitle(s, "Limits of Rule-Based Systems", "Static rules cannot keep up with fraudsters");
  addCard(s, 0.6, 2.1, 5.6, 1.4, "Typical rule",
    "IF amount > 10,000  THEN block\nSimple, but blind to context.", C.amber);
  addBullets(s, [
    "Static thresholds — easy to bypass",
    "Too many false alerts on genuine customers",
    "Fraudsters learn the limits and stay just under them",
    "No memory of past behaviour (no sequence view)",
  ], { x: 0.7, y: 3.8, w: 5.7 });

  addCard(s, 6.7, 2.1, 6.0, 3.6, "Rule vs Behaviour",
    "A 9,000 payment may be perfectly normal for one customer and a clear fraud for another. A fixed number cannot tell the difference — but the customer's recent behaviour can.", C.red);

  s.addNotes(notes([
    { who: "Krishna Mathur", text:
      "Banks already use rule-based systems, so why move to deep learning? Consider a simple rule: if the amount is over ten thousand, block it. This has four big problems. The thresholds are static, so they are easy to bypass. They create many false alerts, annoying genuine customers. Fraudsters quickly learn the limit and simply stay just under it. And critically, rules have no memory — they look at one transaction in isolation. A nine thousand payment might be totally normal for a business account but a clear fraud for a student account. A fixed number cannot tell the difference. The customer's behaviour over time can — and that is what we model next." },
  ]));
}

/* ====================================================================== *
 *  SLIDE 6 — WHY DEEP LEARNING / LSTM
 * ====================================================================== */
{
  const s = newSlide();
  addTitle(s, "Why Deep Learning & LSTM", "A model with memory of past behaviour");
  addCard(s, 0.6, 2.1, 5.9, 1.5, "Normal ML",
    "Sees ONE transaction at a time. No sense of history or order.", C.gray);
  addCard(s, 0.6, 3.75, 5.9, 1.95, "LSTM / RNN",
    "Reads a SEQUENCE of transactions in order and remembers past behaviour — so it spots a sudden break in the pattern.", C.cyan);

  addCard(s, 6.8, 2.1, 5.9, 1.6, "Normal pattern",
    "100  →  150  →  120  →  90\nSteady, small amounts.", C.green);
  addCard(s, 6.8, 3.85, 5.9, 1.85, "Suspicious pattern",
    "100  →  120  →  9,000  →  9,500  →  balance 0\nThe LSTM remembers the calm history and flags the spike.", C.red);

  s.addNotes(notes([
    { who: "Krishna Mathur", text:
      "This slide is the heart of the why. A normal machine-learning model looks at one transaction at a time — it has no sense of order or history. An LSTM, which stands for Long Short-Term Memory, is a recurrent neural network that reads a sequence of transactions in order and keeps a memory of what came before. Look at the example. A normal customer goes 100, 150, 120, 90 — steady and small. A fraud case goes 100, 120, then suddenly 9,000, 9,500, and the balance hits zero. Judged alone, a 9,000 payment is just a big number. But the LSTM remembers the calm history right before it, so the sudden spike stands out immediately. That memory of behaviour is exactly why we chose an LSTM. Now Yash will walk you through the data." },
  ]));
}

/* ====================================================================== *
 *  SLIDE 7 — DATASET OVERVIEW
 * ====================================================================== */
{
  const s = newSlide();
  addTitle(s, "Dataset Overview", "PaySim mobile-money transactions");
  addBullets(s, [
    "step — time (1 step = 1 hour)",
    "type — PAYMENT / TRANSFER / CASH_OUT / DEBIT / CASH_IN",
    "amount — transaction value",
    "nameOrig — sender ID",
    "oldbalanceOrg / newbalanceOrig — sender balance before / after",
  ], { y: 2.0, w: 6.3, fontSize: 16 });
  addBullets(s, [
    "nameDest — receiver ID",
    "oldbalanceDest / newbalanceDest — receiver before / after",
    "isFraud — the label (1 = fraud)",
  ], { x: 7.0, y: 2.0, w: 5.7, fontSize: 16 });
  addCard(s, 7.0, 4.0, 5.7, 1.7, "Important",
    "PaySim is synthetic but realistic. We ship a small sample so everything runs; final metrics use the real PaySim file (data/paysim.csv).", C.amber);

  s.addNotes(notes([
    { who: "Yash Petkar", text:
      "Thank you Krishna. I will cover the data. We use the PaySim dataset, which simulates mobile-money transactions and is widely used for fraud research. Each row is one transaction. The key columns are: step, which is time in hours; type, which is the kind of transaction such as transfer or cash-out; amount; the sender ID and the sender's balance before and after; the receiver ID and their balance before and after; and finally isFraud, which is our label. One honesty note: PaySim is synthetic, and for the demo we generate a small sample so the notebook and dashboard always run. For final, real numbers we drop the full PaySim file into the data folder and re-run. We never report fake accuracy." },
  ]));
}

/* ====================================================================== *
 *  SLIDE 8 — FEATURE ENGINEERING
 * ====================================================================== */
{
  const s = newSlide();
  addTitle(s, "Feature Engineering", "Turning raw columns into fraud signals");
  const feats = [
    ["origin_balance_change", "How much the sender's balance dropped"],
    ["destination_balance_change", "How much the receiver's balance rose"],
    ["amount_to_balance_ratio", "Payment size vs the old balance"],
    ["zero_balance_flag", "Did the sender drain to ~0?"],
    ["high_amount_flag", "Is the amount unusually large?"],
    ["transaction_count_by_customer", "How active is this customer?"],
    ["encoded transaction type", "Type as a number for the model"],
  ];
  feats.forEach((f, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    addCard(s, 0.6 + col * 6.2, 2.0 + row * 1.05, 5.95, 0.92, f[0], f[1],
      i % 2 ? C.cyan : C.blueLt);
  });

  s.addNotes(notes([
    { who: "Yash Petkar", text:
      "Raw columns alone are not enough, so we engineer features that capture the fraud story. Origin balance change shows how much the sender lost. Destination balance change shows how much the receiver gained. Amount-to-balance ratio tells us if the payment is huge relative to what the customer had. The zero-balance flag marks accounts drained to nearly zero — a very strong fraud signal. The high-amount flag marks unusually large payments. Transaction count by customer measures how active the customer is. And we encode the transaction type as a number so the network can use it. Each of these directly reflects the suspicious behaviour we saw earlier, and all of it lives in one clean module, feature_engineering dot py." },
  ]));
}

/* ====================================================================== *
 *  SLIDE 9 — SEQUENCE CREATION
 * ====================================================================== */
{
  const s = newSlide();
  addTitle(s, "Sequence Creation Logic", "From a flat table to time-ordered windows");
  addFlow(s, [
    { label: "T1" }, { label: "T2" }, { label: "T3" }, { label: "T4" },
    { label: "T5", color: C.cyan }, { label: "T6", color: C.red },
  ], 2.4);
  addCard(s, 0.6, 3.7, 5.9, 1.9, "Input window  →  T1 … T5",
    "Sort each customer by time, then slide a window of the last transactions.", C.blueLt);
  addCard(s, 6.8, 3.7, 5.9, 1.9, "Prediction  →  Is T6 fraud?",
    "The model uses the window of past behaviour to score the NEXT transaction.", C.red);

  s.addNotes(notes([
    { who: "Yash Petkar", text:
      "Here is how we prepare data for a sequence model. For each customer, we sort their transactions in time order. Then we slide a window — in our project, length ten. The window of past transactions, say T1 to T5 in this simple diagram, becomes the input. The very next transaction, T6, is what we try to predict: is it fraud or not. We never mix transactions from different customers, and we keep time order so there is no cheating. The result is a three-dimensional array: number of samples, by sequence length, by number of features. That shape is exactly what the LSTM expects. Now Atharva will explain the model itself." },
  ]));
}

/* ====================================================================== *
 *  SLIDE 10 — SYSTEM ARCHITECTURE
 * ====================================================================== */
{
  const s = newSlide();
  addTitle(s, "Full System Architecture", "End-to-end fraud detection pipeline");
  addFlow(s, [
    { label: "Transaction\nData" },
    { label: "Cleaning" },
    { label: "Feature\nEngineering" },
    { label: "Sequence\nBuilder", color: C.cyan },
    { label: "LSTM\nModel", color: C.cyan },
  ], 2.6, { h: 1.0 });
  addFlow(s, [
    { label: "Fraud\nScore", color: C.amber },
    { label: "Dashboard" },
    { label: "Business\nAction", color: C.green },
  ], 4.2, { h: 1.0, x: 2.0, w: 9.3 });
  addCard(s, 0.6, 5.6, 12.1, 1.0, "One pipeline, modular code",
    "Each stage is a separate, tested module in src/. The same code powers the notebook AND the live dashboard.", C.blue);

  s.addNotes(notes([
    { who: "Atharva Soundankar", text:
      "Thanks Yash. Let me show the full system. Raw transaction data comes in. We clean it, engineer the features Yash described, and then the sequence builder turns it into time-ordered windows. Those windows go into the LSTM model, which outputs a fraud score between zero and one. That score flows into the dashboard, and finally into a business action — approve, review, or block. The important engineering point is that every stage is a separate, tested Python module in the src folder, and the exact same code runs both in our training notebook and in the live Streamlit dashboard. That means what we train is what we deploy — no surprises." },
  ]));
}

/* ====================================================================== *
 *  SLIDE 11 — LSTM ARCHITECTURE
 * ====================================================================== */
{
  const s = newSlide();
  addTitle(s, "LSTM Model Architecture", "Compact, regularised, production-friendly");
  addFlow(s, [
    { label: "Input\n(seq × features)" },
    { label: "LSTM\n64 units", color: C.cyan },
    { label: "Dropout\n0.3" },
    { label: "Dense\n32 ReLU" },
    { label: "Sigmoid\nfraud prob", color: C.green },
  ], 2.6, { h: 1.1 });
  addCard(s, 0.6, 4.2, 5.9, 1.6, "Why this shape",
    "LSTM captures sequence memory; dropout fights overfitting; the sigmoid gives a probability we can threshold.", C.blueLt);
  addCard(s, 6.8, 4.2, 5.9, 1.6, "Training choices",
    "Binary cross-entropy loss · Adam optimizer · CLASS WEIGHTS to handle rare fraud (heavy imbalance).", C.amber);

  s.addNotes(notes([
    { who: "Atharva Soundankar", text:
      "Here is the model architecture. The input is a sequence: ten time steps, each with our twelve features. It goes into an LSTM layer with sixty-four units, which is where the sequence memory lives. Then a dropout layer of zero point three randomly switches off neurons during training to prevent overfitting. Next a dense layer with thirty-two units and ReLU activation learns higher-level combinations. Finally a single neuron with a sigmoid activation outputs a fraud probability between zero and one. We train with binary cross-entropy loss and the Adam optimizer. Crucially, because fraud is rare, we use class weights so the model pays extra attention to the few fraud cases instead of ignoring them. We also build a simple Dense baseline that flattens the sequence, to prove the LSTM's memory actually helps." },
  ]));
}

/* ====================================================================== *
 *  SLIDE 12 — EVALUATION PLAN
 * ====================================================================== */
{
  const s = newSlide();
  addTitle(s, "Model Evaluation Plan", "Recall matters most for fraud");
  const metrics = [
    ["Accuracy", "Overall correctness (misleading when fraud is rare)"],
    ["Precision", "Of flagged frauds, how many were real"],
    ["Recall", "Of real frauds, how many we caught — KEY metric"],
    ["F1-score", "Balance of precision and recall"],
    ["ROC-AUC", "Ranking quality across thresholds"],
    ["PR-AUC", "Best metric for the rare fraud class"],
  ];
  metrics.forEach((m, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const acc = m[0] === "Recall" ? C.red : C.blueLt;
    addCard(s, 0.6 + col * 4.15, 2.1 + row * 1.55, 3.9, 1.4, m[0], m[1], acc);
  });
  s.addText("Plus a confusion matrix — and we report 'Update after running on real dataset' until trained on real PaySim.", {
    x: 0.6, y: 5.5, w: 12.1, h: 0.5, fontFace: FONT, fontSize: 13, color: C.amber, italic: true,
  });

  s.addNotes(notes([
    { who: "Atharva Soundankar", text:
      "How do we judge the model? We use six metrics plus a confusion matrix. Accuracy is the overall correctness, but it is misleading when fraud is rare — a model that says no to everything can still look ninety-nine percent accurate. Precision asks: of the transactions we flagged, how many were really fraud. Recall asks: of all the real frauds, how many did we catch — and this is our most important metric, because missing a real fraud is far more expensive than reviewing a genuine payment by mistake. F1 balances precision and recall. ROC-AUC and PR-AUC measure ranking quality, and PR-AUC is especially good for imbalanced fraud data. Finally, an important integrity point: until we train on the real PaySim dataset, every metric in our report literally says update after running on real dataset. We never invent numbers." },
  ]));
}

/* ====================================================================== *
 *  SLIDE 13 — DASHBOARD
 * ====================================================================== */
{
  const s = newSlide();
  addTitle(s, "FraudShield AI Dashboard", "Ten analyst-ready pages, one product");
  const tabs = [
    "Executive Overview", "Dataset Explorer", "Fraud Risk Scoring",
    "Customer Sequence Analyzer", "Fraud Pattern Insights", "Model Performance",
    "Explainability Panel", "Alert Center", "Business Impact Simulator", "Recommendations",
  ];
  tabs.forEach((t, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    addCard(s, 0.6 + col * 6.2, 2.0 + row * 0.86, 5.95, 0.74, `${i + 1}.  ${t}`, "",
      i % 2 ? C.cyan : C.blueLt);
  });

  s.addNotes(notes([
    { who: "Krishna Mathur", text:
      "Now the part people actually use — the dashboard. We built ten pages, each for a real job. Executive Overview gives leadership the headline numbers. Dataset Explorer lets you inspect the data. Fraud Risk Scoring scores an uploaded file. The Customer Sequence Analyzer shows one customer's last ten transactions and explains the behaviour. Fraud Pattern Insights shows where fraud concentrates. Model Performance shows the metrics. The Explainability Panel gives a plain-English reason for each alert. The Alert Center is the fraud team's work queue with CSV export. The Business Impact Simulator turns detection into money saved. And Recommendations summarises guidance, limitations and ethics. The whole thing runs with one command, and if the trained model is missing it still works in a transparent demo mode. We will show a short live demo after this." },
  ]));
}

/* ====================================================================== *
 *  SLIDE 14 — BUSINESS IMPACT
 * ====================================================================== */
{
  const s = newSlide();
  addTitle(s, "Business Impact", "From a model score to measurable value");
  const items = [
    ["Reduce fraud loss", "Stop money leaving before approval."],
    ["Detect early", "Catch suspicious behaviour as it builds."],
    ["Less manual work", "Auto-approve low risk; focus analysts on high risk."],
    ["Improve trust", "Fewer false alarms for genuine customers."],
    ["Prioritise risk", "Rank transactions so the worst are handled first."],
  ];
  items.forEach((it, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    addCard(s, 0.6 + col * 4.15, 2.1 + row * 1.75, 3.9, 1.6, it[0], it[1],
      [C.green, C.cyan, C.blueLt, C.amber, C.blue][i]);
  });

  s.addNotes(notes([
    { who: "Krishna Mathur", text:
      "What is the business payoff? Five things. We reduce fraud loss by scoring before the payment is approved, so money never leaves. We detect suspicious behaviour early, as the pattern builds, instead of after the fact. We cut manual workload — low-risk payments are auto-approved and analysts focus only on the high-risk queue. We improve customer trust because fewer genuine customers get falsely blocked. And we prioritise risk, ranking transactions so the worst cases are handled first. In our Business Impact Simulator you can plug in your own numbers — average fraud loss, review cost — and it estimates the net savings. That turns a technical score into a board-level business case." },
  ]));
}

/* ====================================================================== *
 *  SLIDE 15 — LIMITATIONS & ETHICS
 * ====================================================================== */
{
  const s = newSlide();
  addTitle(s, "Limitations & Ethics", "Honest about what this is — and is not");
  addBullets(s, [
    "PaySim is synthetic — not real customer data",
    "Real bank data is private and hard to obtain",
    "Fraud patterns change over time (model drift)",
    "False positives inconvenience genuine customers",
  ], { y: 2.1, w: 6.2 });
  addCard(s, 7.0, 2.1, 5.7, 1.6, "Human-in-the-loop",
    "The model recommends; a human decides on high-impact cases.", C.green);
  addCard(s, 7.0, 3.85, 5.7, 1.85, "Data privacy & fairness",
    "Transaction data is sensitive. Protect it, control access, and monitor that the model does not unfairly target any group.", C.amber);

  s.addNotes(notes([
    { who: "4th member", text:
      "I will cover limitations and ethics, and we want to be honest here. First, our demo uses PaySim, which is synthetic data — real customer transactions are private and very hard to obtain, so real-world results may differ. Second, fraud patterns change constantly; a model trained today will slowly decay, which we call model drift, so it must be retrained. Third, false positives are a real cost — every genuine customer we wrongly block is a bad experience. On ethics, three principles guide us. We keep a human in the loop: the model only recommends, and a person makes the final call on high-impact cases. We protect data privacy, because transaction data is highly sensitive. And we monitor fairness, making sure the model does not unfairly target any particular group of customers. Responsible use is part of the design, not an afterthought." },
  ]));
}

/* ====================================================================== *
 *  SLIDE 16 — FUTURE SCOPE & CONCLUSION
 * ====================================================================== */
{
  const s = newSlide();
  addTitle(s, "Future Scope & Conclusion", "Where FraudShield AI goes next");
  const future = [
    ["⚡ Real-time fraud API", "Score every payment in milliseconds."],
    ["🔐 OTP / SMS step-up", "Verify medium-risk payments instantly."],
    ["🔁 Analyst feedback loop", "Confirmed outcomes retrain the model."],
    ["🧠 Explainable AI (SHAP)", "Richer per-feature reasons."],
    ["☁️ Cloud deployment", "Scalable, with auto-retraining."],
  ];
  future.forEach((f, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    addCard(s, 0.6 + col * 4.15, 2.0 + row * 1.55, 3.9, 1.4, f[0], f[1],
      [C.cyan, C.blueLt, C.green, C.amber, C.blue][i]);
  });
  addCard(s, 0.6, 5.2, 12.1, 1.2, "Conclusion",
    "FraudShield AI turns a customer's transaction sequence into a fraud score and a clear business action — combining an LSTM with a premium analyst dashboard. Thank you. Questions?", C.green);

  s.addNotes(notes([
    { who: "4th member", text:
      "Finally, the future scope. We would build a real-time fraud API that scores each payment in milliseconds. We would add OTP or SMS step-up verification for medium-risk payments. We would close the loop so confirmed analyst decisions automatically retrain the model. We would add explainable AI techniques like SHAP for even richer reasons. And we would deploy to the cloud with automatic retraining so the model never goes stale. To conclude: FraudShield AI takes a customer's transaction sequence, turns it into a fraud risk score using an LSTM, and maps that score to a clear business action — all wrapped in a professional dashboard a fraud team can actually use. Thank you very much for listening. We are happy to take any questions, and we can show a quick live demo of the dashboard now." },
  ]));
}

/* --------------------------------------------------------------- write out */
const outFile = path.join(__dirname, "FraudShield_AI_Payment_Fraud_LSTM.pptx");
pptx.writeFile({ fileName: outFile })
  .then((f) => console.log("✅ Presentation written:", f))
  .catch((e) => {
    console.error("❌ Failed to write presentation:", e);
    process.exit(1);
  });
