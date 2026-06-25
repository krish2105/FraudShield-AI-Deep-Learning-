# FraudShield AI — Speaker Script

Simple English. Target length: **10–15 minutes**. These notes are also embedded
in the `.pptx` (Presenter View) via `slide.addNotes()`.

**Speaker plan**
- **Krishna Mathur** — intro, business problem, dashboard, conclusion (slides 1–6, 13, 14)
- **Yash Petkar** — dataset, preprocessing, feature engineering (slides 7–9)
- **Atharva Soundankar** — LSTM architecture, model training, evaluation (slides 10–12)
- **4th member (__________)** — limitations, ethics, future scope (slides 15–16)

---

## Slide 1 — Title  · *Krishna Mathur*
Good morning everyone. We are Team FraudShield AI. Our project detects payment
fraud using deep learning. The key idea is simple: instead of judging one
transaction alone, we look at a customer's recent **sequence** of transactions
and decide if the next payment is fraud. Krishna covers the problem and business
value, Yash covers data and features, Atharva covers the LSTM and evaluation,
and our fourth member covers limitations, ethics and future scope. This will
take about 12 minutes.

## Slide 2 — Executive Summary · *Krishna Mathur*
Our project in three business sentences. One, we look at behaviour over time,
not one isolated payment. Two, we use an LSTM — a network with memory — to learn
suspicious patterns simple rules miss. Three, every transaction gets a fraud
score mapped to a clear action: Approve, Review/OTP, or Block. The output is a
decision, not just a number.

## Slide 3 — Business Problem · *Krishna Mathur*
Payments happen in seconds and fraudsters exploit that. The typical attack: an
account behaves normally, then a sudden large transfer, a quick cash-out, and
the balance is drained to zero. By the time a human notices, the money is gone.
Investigating every payment manually is very expensive. Banks need automatic,
real-time detection of these suspicious sequences.

## Slide 4 — Why It Matters · *Krishna Mathur*
Five business impacts: financial loss on every missed fraud; lost customer
trust; regulatory fines; analyst overload; and reputation damage. A good
detection system protects all five — this is a board-level priority.

## Slide 5 — Limits of Rules · *Krishna Mathur*
Banks use rules like "if amount over 10,000, block." Four problems: thresholds
are static and easy to bypass; too many false alerts; fraudsters stay just under
the limit; and rules have no memory. A 9,000 payment can be normal for one
customer and fraud for another — a fixed number cannot tell, but behaviour can.

## Slide 6 — Why Deep Learning & LSTM · *Krishna Mathur*
This is the heart of the why. Normal ML sees one transaction with no order. An
LSTM reads a sequence in order and remembers the past. Normal: 100, 150, 120,
90 — steady. Fraud: 100, 120, then 9,000, 9,500, balance zero. Alone, 9,000 is
just a big number; after a calm history the spike stands out. That memory is why
we chose an LSTM. Over to Yash for the data.

## Slide 7 — Dataset Overview · *Yash Petkar*
Thanks Krishna. We use PaySim, a widely-used mobile-money fraud dataset. Each
row is a transaction: step (time in hours), type, amount, sender ID and balances
before/after, receiver ID and balances, and isFraud, our label. Honesty note:
PaySim is synthetic, and for the demo we generate a small sample so everything
runs. For real numbers we drop the full PaySim file in `data/paysim.csv` and
re-run. We never report fake accuracy.

## Slide 8 — Feature Engineering · *Yash Petkar*
Raw columns are not enough, so we engineer signals. Origin balance change (how
much the sender lost), destination balance change (how much the receiver
gained), amount-to-balance ratio (payment size vs balance), a zero-balance flag
(drained to near zero — strong signal), a high-amount flag, transaction count
per customer (activity), and an encoded transaction type. Each captures the
fraud story, all in one clean module.

## Slide 9 — Sequence Creation · *Yash Petkar*
For each customer we sort transactions by time, then slide a window of length
ten. The window of past transactions is the input; the next transaction is what
we predict. We never mix customers and we keep time order, so no cheating. The
result is a 3D array: samples × sequence length × features — exactly what the
LSTM needs. Over to Atharva.

## Slide 10 — System Architecture · *Atharva Soundankar*
Thanks Yash. The full pipeline: raw data → cleaning → feature engineering →
sequence builder → LSTM → fraud score → dashboard → business action. The key
engineering point: every stage is a separate, tested module in `src/`, and the
same code runs in the notebook and the live dashboard. What we train is what we
deploy.

## Slide 11 — LSTM Architecture · *Atharva Soundankar*
The input is ten time steps of twelve features. It goes into an LSTM of 64 units
(the memory), then dropout 0.3 to prevent overfitting, then a dense layer of 32
ReLU units, then one sigmoid neuron giving a fraud probability. We train with
binary cross-entropy and Adam, and — because fraud is rare — class weights so
the model focuses on the few fraud cases. We also build a Dense baseline that
flattens the sequence, to prove the LSTM's memory helps.

## Slide 12 — Evaluation Plan · *Atharva Soundankar*
Six metrics plus a confusion matrix. Accuracy is misleading when fraud is rare.
Precision: of those flagged, how many were real. Recall: of all real frauds, how
many we caught — our most important metric, because missing fraud is costly. F1
balances the two. ROC-AUC and PR-AUC measure ranking; PR-AUC is best for
imbalanced data. Integrity point: until trained on real PaySim, our report says
"Update after running on real dataset." We never invent numbers.

## Slide 13 — Dashboard · *Krishna Mathur*
Now the part people use. Ten pages: Executive Overview for leadership; Dataset
Explorer; Fraud Risk Scoring on an uploaded file; the Customer Sequence Analyzer
that explains one customer's last ten transactions; Fraud Pattern Insights;
Model Performance; the Explainability Panel with plain-English reasons; the Alert
Center work queue with CSV export; the Business Impact Simulator; and
Recommendations. One command runs it, and if the model is missing it still works
in transparent demo mode.

## Slide 14 — Business Impact · *Krishna Mathur*
Five payoffs: reduce fraud loss by scoring before approval; detect behaviour
early; cut manual workload by auto-approving low risk; improve trust with fewer
false alarms; and prioritise the worst cases first. The Business Impact
Simulator turns the score into estimated net savings — a board-level case.

## Slide 15 — Limitations & Ethics · *4th member (__________)*
Being honest: our demo uses synthetic PaySim data; real data is private, so
results may differ. Fraud patterns drift, so the model must be retrained. False
positives are a real cost. On ethics: we keep a human in the loop — the model
recommends, a person decides; we protect data privacy; and we monitor fairness
so no group is unfairly targeted. Responsible use is part of the design.

## Slide 16 — Future Scope & Conclusion · *4th member (__________)*
Future work: a real-time fraud API; OTP/SMS step-up for medium risk; an analyst
feedback loop that retrains the model; explainable AI like SHAP; and cloud
deployment with auto-retraining. To conclude: FraudShield AI turns a customer's
transaction sequence into a fraud score and a clear business action, using an
LSTM and a premium dashboard a fraud team can actually use. Thank you — we are
happy to take questions and can show a quick live demo.
