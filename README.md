# Daniel Perez | Interactive Engineering Portfolio

> A high-performance, 3D-interactive web portfolio demonstrating capabilities in AI data evaluation, satellite remote sensing, and full-stack spatial web development. 

Live Site: [0datadan.github.io](https://0datadan.github.io)

---

## 🏗️ Architecture & Interaction Design

This portfolio breaks away from standard static templates by employing a unified `requestAnimationFrame` loop that seamlessly couples DOM elements with a background WebGL context. 

### Core Engineering Features
* **Magnetic Particle Cursor:** Custom spring physics algorithm running on the canvas to attract target nodes within a specific proximity threshold, creating a liquid, magnetic interaction model.
* **3D Node Map:** A collision-free, math-driven radial ledger mapped in 2D space, immune to 3D CSS transform glitches.
* **Hardware-Accelerated UI:** Implements `translate3d`, `translateZ`, and `will-change` properties to maintain strict 60 FPS performance during heavy DOM manipulation (like the 3D blueprint card flips).

---

## 🛠️ Tech Stack 

* **Frontend:** Vanilla JavaScript (ES6+), HTML5, CSS3
* **Styling:** Tailwind CSS (via CDN for rapid prototyping), custom keyframe animations
* **3D & Canvas:** Three.js (r128)
* **Typography:** JetBrains Mono (Terminal readouts), Plus Jakarta Sans (Primary UI)

---

## 🚀 Local Development

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/0DataDan/0datadan.github.io.git](https://github.com/0DataDan/0datadan.github.io.git)
   cd 0datadan.github.io