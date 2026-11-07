import Mathlib

/-!
# Directions, log lengths and squared lengths of the plane

The closure engine (`side/geo_closure.py`) proves a statement by linear algebra over three kinds of variable: the direction of a line, modulo π; the log of a length;
the square of a length. This file gives each a meaning on real coordinates, and proves that a polynomial fact about a figure and the linear relation the engine writes for it say the same thing.
Nothing here is assumed: there are no axioms beyond Lean's own.
-/

noncomputable section
open Complex

namespace GeoCert

/-- a point of the plane, by its coordinates -/
@[ext] structure P where
  x : ℝ
  y : ℝ

/-- the cross product of the vectors ab and cd -/
def cr (a b c d : P) : ℝ := (b.x - a.x) * (d.y - c.y) - (b.y - a.y) * (d.x - c.x)
/-- the dot product of the vectors ab and cd -/
def dt (a b c d : P) : ℝ := (b.x - a.x) * (d.x - c.x) + (b.y - a.y) * (d.y - c.y)
/-- the squared length of ab -/
def d2 (a b : P) : ℝ := (b.x - a.x) ^ 2 + (b.y - a.y) ^ 2

theorem d2_comm (a b : P) : d2 a b = d2 b a := by unfold d2; ring
theorem d2_self (a : P) : d2 a a = 0 := by unfold d2; ring

theorem d2_pos {a b : P} (h : a ≠ b) : 0 < d2 a b := by
  unfold d2
  by_contra hc
  apply h
  have h1 : 0 ≤ (b.x - a.x) ^ 2 := sq_nonneg _
  have h2 : 0 ≤ (b.y - a.y) ^ 2 := sq_nonneg _
  have h3 : (b.x - a.x) ^ 2 = 0 := by linarith
  have h4 : (b.y - a.y) ^ 2 = 0 := by linarith
  have h5 : b.x - a.x = 0 := by simpa using h3
  have h6 : b.y - a.y = 0 := by simpa using h4
  ext <;> linarith

/-- lines ab and cd are parallel -/
def Para (a b c d : P) : Prop := cr a b c d = 0
/-- lines ab and cd are perpendicular -/
def Perp (a b c d : P) : Prop := dt a b c d = 0
/-- the angle from line ab to line cd equals the angle from line ef to line gh, modulo π -/
def EqA (a b c d e f g h : P) : Prop := dt a b c d * cr e f g h - cr a b c d * dt e f g h = 0
/-- ab = cd -/
def Cong (a b c d : P) : Prop := d2 a b = d2 c d
/-- ab · gh = cd · ef -/
def Ratio (a b c d e f g h : P) : Prop := d2 a b * d2 g h = d2 c d * d2 e f
/-- ab = 2 · cd -/
def Half (a b c d : P) : Prop := d2 a b = 4 * d2 c d

/-- the vector ab as a complex number -/
def zc (a b : P) : ℂ := ⟨b.x - a.x, b.y - a.y⟩

theorem zc_ne {a b : P} (h : a ≠ b) : zc a b ≠ 0 := by
  intro hz
  apply h
  have h1 := congrArg Complex.re hz
  have h2 := congrArg Complex.im hz
  simp [zc] at h1 h2
  ext <;> linarith

/-- the direction of line ab as a point of the unit circle: the double of its angle -/
def dirc (a b : P) : ℂ := zc a b / (starRingEnd ℂ) (zc a b)

/-- the direction of line ab, a real number in (-π/2, π/2]: it does not depend on the order of a and b -/
def U (a b : P) : ℝ := Complex.arg (dirc a b) / 2

theorem zc_swap (a b : P) : zc b a = - zc a b := by
  apply Complex.ext <;> simp [zc]

theorem dirc_comm (a b : P) : dirc a b = dirc b a := by
  unfold dirc
  rw [zc_swap a b, map_neg, neg_div_neg_eq]

theorem U_comm (a b : P) : U a b = U b a := by unfold U; rw [dirc_comm]

/-- the isomorphism of ℝ modulo π with the unit circle -/
def ee (t : ℝ) : ℂ := exp (((2 * t : ℝ) : ℂ) * I)

theorem ee_add (s t : ℝ) : ee (s + t) = ee s * ee t := by
  unfold ee
  rw [← Complex.exp_add]
  congr 1
  push_cast
  ring

theorem ee_ne (t : ℝ) : ee t ≠ 0 := Complex.exp_ne_zero _

theorem ee_sub (s t : ℝ) : ee (s - t) = ee s / ee t := by
  unfold ee
  rw [← Complex.exp_sub]
  congr 1
  push_cast
  ring

theorem conj_ne {z : ℂ} (h : z ≠ 0) : (starRingEnd ℂ) z ≠ 0 := by
  simpa using h

theorem abs_dirc {a b : P} (h : a ≠ b) : Complex.abs (dirc a b) = 1 := by
  unfold dirc
  rw [map_div₀, Complex.abs_conj]
  exact div_self (by simpa using zc_ne h)

theorem ee_U {a b : P} (h : a ≠ b) : ee (U a b) = dirc a b := by
  have h1 := Complex.abs_mul_exp_arg_mul_I (dirc a b)
  rw [abs_dirc h] at h1
  unfold ee U
  simp only [Complex.ofReal_one, one_mul] at h1
  have : (((2 * (Complex.arg (dirc a b) / 2) : ℝ)) : ℂ) = ((Complex.arg (dirc a b) : ℝ) : ℂ) := by
    congr 1
    ring
  rw [this]
  exact h1

/-- r is a multiple of π: equality of directions -/
def ModPi (r : ℝ) : Prop := ∃ k : ℤ, r = k * Real.pi

theorem modPi_iff (r : ℝ) : ModPi r ↔ ee r = 1 := by
  unfold ModPi ee
  rw [Complex.exp_eq_one_iff]
  constructor
  · rintro ⟨k, hk⟩
    refine ⟨k, ?_⟩
    rw [hk]
    push_cast
    ring
  · rintro ⟨n, hn⟩
    refine ⟨n, ?_⟩
    have h := congrArg Complex.im hn
    simp at h
    have hpi := Real.pi_pos
    linarith

theorem ModPi.add {r s : ℝ} (h : ModPi r) (g : ModPi s) : ModPi (r + s) := by
  obtain ⟨k, hk⟩ := h
  obtain ⟨l, hl⟩ := g
  exact ⟨k + l, by rw [hk, hl]; push_cast; ring⟩

theorem ModPi.zmul {r : ℝ} (n : ℤ) (h : ModPi r) : ModPi ((n : ℝ) * r) := by
  obtain ⟨k, hk⟩ := h
  exact ⟨n * k, by rw [hk]; push_cast; ring⟩

theorem ModPi.int (n : ℤ) : ModPi ((n : ℝ) * Real.pi) := ⟨n, rfl⟩

theorem ModPi.zero : ModPi 0 := ⟨0, by simp⟩

theorem ModPi.congr {r s : ℝ} (e : r = s) (h : ModPi r) : ModPi s := e ▸ h

theorem div_conj_one {w : ℂ} (hw : w ≠ 0) : w / (starRingEnd ℂ) w = 1 ↔ w.im = 0 := by
  rw [div_eq_one_iff_eq (conj_ne hw)]
  constructor
  · intro h
    exact Complex.conj_eq_iff_im.mp h.symm
  · intro h
    exact (Complex.conj_eq_iff_im.mpr h).symm

theorem div_conj_neg {w : ℂ} (hw : w ≠ 0) : w / (starRingEnd ℂ) w = -1 ↔ w.re = 0 := by
  rw [div_eq_iff (conj_ne hw)]
  constructor
  · intro h
    have := congrArg Complex.re h
    simp at this
    linarith
  · intro h
    apply Complex.ext <;> simp [h]

theorem ee_half : ee (Real.pi / 2) = -1 := by
  unfold ee
  have : (((2 * (Real.pi / 2) : ℝ)) : ℂ) = (Real.pi : ℂ) := by
    congr 1
    ring
  rw [this, Complex.exp_pi_mul_I]

theorem para_iff {a b c d : P} (h1 : a ≠ b) (h2 : c ≠ d) : Para a b c d ↔ ModPi (U a b - U c d) := by
  have z1 := zc_ne h1
  have z2 := zc_ne h2
  have w0 : zc a b * (starRingEnd ℂ) (zc c d) ≠ 0 := mul_ne_zero z1 (conj_ne z2)
  rw [modPi_iff, ee_sub, ee_U h1, ee_U h2]
  have e : dirc a b / dirc c d = (zc a b * (starRingEnd ℂ) (zc c d)) / (starRingEnd ℂ) (zc a b * (starRingEnd ℂ) (zc c d)) := by
    unfold dirc
    have c1 := conj_ne z1
    have c2 := conj_ne z2
    simp only [map_mul, Complex.conj_conj]
    field_simp
  rw [e, div_conj_one w0]
  unfold Para cr
  simp [zc, Complex.mul_im]
  constructor <;> intro h <;> linarith

theorem perp_iff {a b c d : P} (h1 : a ≠ b) (h2 : c ≠ d) : Perp a b c d ↔ ModPi (U a b - U c d - Real.pi / 2) := by
  have z1 := zc_ne h1
  have z2 := zc_ne h2
  have w0 : zc a b * (starRingEnd ℂ) (zc c d) ≠ 0 := mul_ne_zero z1 (conj_ne z2)
  rw [modPi_iff, ee_sub, ee_sub, ee_U h1, ee_U h2, ee_half]
  have e : dirc a b / dirc c d = (zc a b * (starRingEnd ℂ) (zc c d)) / (starRingEnd ℂ) (zc a b * (starRingEnd ℂ) (zc c d)) := by
    unfold dirc
    have c1 := conj_ne z1
    have c2 := conj_ne z2
    simp only [map_mul, Complex.conj_conj]
    field_simp
  have e2 : ∀ q : ℂ, q / (-1) = 1 ↔ q = -1 := by
    intro q
    constructor
    · intro h
      have : q = -1 := by
        have := h
        rw [div_neg, div_one] at this
        exact neg_eq_iff_eq_neg.mp this
      exact this
    · intro h
      rw [h]
      norm_num
  rw [e2, e, div_conj_neg w0]
  unfold Perp dt
  simp [zc, Complex.mul_re]
  constructor <;> intro h <;> linarith

theorem eqa_iff {a b c d e f g h : P} (h1 : a ≠ b) (h2 : c ≠ d) (h3 : e ≠ f) (h4 : g ≠ h) :
    EqA a b c d e f g h ↔ ModPi (U a b - U c d - U e f + U g h) := by
  have z1 := zc_ne h1
  have z2 := zc_ne h2
  have z3 := zc_ne h3
  have z4 := zc_ne h4
  have c1 := conj_ne z1
  have c2 := conj_ne z2
  have c3 := conj_ne z3
  have c4 := conj_ne z4
  have w0 : zc a b * (starRingEnd ℂ) (zc c d) * ((starRingEnd ℂ) (zc e f) * zc g h) ≠ 0 :=
    mul_ne_zero (mul_ne_zero z1 c2) (mul_ne_zero c3 z4)
  rw [modPi_iff, ee_add, ee_sub, ee_sub, ee_U h1, ee_U h2, ee_U h3, ee_U h4]
  have e0 : dirc a b / dirc c d / dirc e f * dirc g h =
      (zc a b * (starRingEnd ℂ) (zc c d) * ((starRingEnd ℂ) (zc e f) * zc g h)) /
        (starRingEnd ℂ) (zc a b * (starRingEnd ℂ) (zc c d) * ((starRingEnd ℂ) (zc e f) * zc g h)) := by
    unfold dirc
    simp only [map_mul, Complex.conj_conj]
    field_simp
    ring
  rw [e0, div_conj_one w0]
  unfold EqA dt cr
  simp [zc, Complex.mul_im, Complex.mul_re]
  constructor <;> intro h <;> linarith

/-- the log of a length -/
def W (a b : P) : ℝ := Real.log (d2 a b) / 2

theorem W_comm (a b : P) : W a b = W b a := by unfold W; rw [d2_comm]

theorem cong_iff {a b c d : P} (h1 : a ≠ b) (h2 : c ≠ d) : Cong a b c d ↔ W a b - W c d = 0 := by
  unfold Cong W
  constructor
  · intro h
    rw [h]
    ring
  · intro h
    have : Real.log (d2 a b) = Real.log (d2 c d) := by linarith
    exact Real.log_injOn_pos (Set.mem_Ioi.mpr (d2_pos h1)) (Set.mem_Ioi.mpr (d2_pos h2)) this

theorem ratio_iff {a b c d e f g h : P} (h1 : a ≠ b) (h2 : c ≠ d) (h3 : e ≠ f) (h4 : g ≠ h) :
    Ratio a b c d e f g h ↔ W a b - W c d - W e f + W g h = 0 := by
  have p1 := d2_pos h1
  have p2 := d2_pos h2
  have p3 := d2_pos h3
  have p4 := d2_pos h4
  unfold Ratio W
  have l1 := Real.log_mul p1.ne' p4.ne'
  have l2 := Real.log_mul p2.ne' p3.ne'
  constructor
  · intro hh
    rw [hh, l2] at l1
    linarith
  · intro hh
    have : Real.log (d2 a b * d2 g h) = Real.log (d2 c d * d2 e f) := by
      rw [l1, l2]
      linarith
    exact Real.log_injOn_pos (Set.mem_Ioi.mpr (mul_pos p1 p4)) (Set.mem_Ioi.mpr (mul_pos p2 p3)) this

theorem half_iff {a b c d : P} (h1 : a ≠ b) (h2 : c ≠ d) : Half a b c d ↔ W a b - W c d = Real.log 2 := by
  have p1 := d2_pos h1
  have p2 := d2_pos h2
  have l4 : Real.log 4 = 2 * Real.log 2 := by
    rw [show (4 : ℝ) = 2 ^ 2 by norm_num, Real.log_pow]
    norm_num
  have l := Real.log_mul (show (4 : ℝ) ≠ 0 by norm_num) p2.ne'
  unfold Half W
  constructor
  · intro h
    rw [h, l, l4]
    ring
  · intro h
    have : Real.log (d2 a b) = Real.log (4 * d2 c d) := by
      rw [l, l4]
      linarith
    exact Real.log_injOn_pos (Set.mem_Ioi.mpr p1) (Set.mem_Ioi.mpr (mul_pos (by norm_num) p2)) this

end GeoCert
