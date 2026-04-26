# KisanAlert Project Roadmap 🚀

This roadmap outlines the path to a production-ready agricultural decision support system, focusing on farmer profit maximization and premium user experience.

---

## 📅 Phase 1: UX & Web Optimization (Current)
*Goal: Polish the interface for professional web delivery.*

- [x] **Dynamic Mic Position**: Enable persistent, draggable AI Voice mic for Web.
- [ ] **Responsive Charting**: Optimize `fl_chart` for desktop/tablet views.
- [ ] **Dynamic Theming**: Fine-tune Dark Mode vs Light Mode accessibility for field use.
- [ ] **Localization**: Complete Marathwada-specific Marathi dialect integration across all modals.

---

## 📈 Phase 2: Price Strategy & Intelligence
*Goal: Move from "raw data" to "actionable profit strategies".*

- [ ] **Net Gain Logic**: Backend calculation of `Market Price - (Transport + Commission) = Net Profit`.
- [ ] **Multi-Mandi Ranking**: Expand Lead-Lag engine to compare 15+ mandis across Maharashtra.
- [ ] **Threshold Tuning**: Refine `alert_engine.py` to minimize false "SELL" alarms during minor jitter.
- [ ] **Policy Impact scoring**: Integrate DGFT/NAFED news directly into the crash probability score.

---

## 🛡️ Phase 3: Trust & Verification
*Goal: Build deep trust with the farming community.*

- [ ] **Audit Trail**: Allow farmers to see *why* a prediction was made (e.g., "High arrivals in Latur + Weather risk").
- [ ] **Accuracy Scorecard**: Live "Trust Badge" updates showing historical prediction success.
- [ ] **Community Chopal**: Verified success stories with Agmarknet receipt verification.
- [ ] **Offline Resilience**: PWA (Progressive Web App) support for 100% offline access to cached alerts.

---

## 🎙️ Phase 4: Advanced AI Integration
*Goal: State-of-the-art voice and vision capabilities.*

- [ ] **Gemini Voice 2.0**: Low-latency, natural Marathi conversation for price queries.
- [ ] **Visual Diagnosis**: (Future) Image-based pest/disease detection using Vertex AI.
- [ ] **Hyper-Local Weather**: Integrate village-level precipitation alerts with "Safe Harvest" windows.
- [ ] **Auto-Dialer Integration**: Voice-based automated alerts for high-priority RED signals.

---

## 🚀 Execution Strategy
1. **Develop** in local environment (Port 8000/8080).
2. **Verify** using AI-simulated farmer personas.
3. **Deploy** to Firebase/Cloud Run for stakeholder review.
4. **Iterate** based on real-time Agmarknet market shifts.
