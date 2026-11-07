import GeoBase

/-!
# The rules of the closure, with their conditions

Each theorem is one rule of `side/geo_check.py`. What a rule needs beyond its premises is a hypothesis here, so this file states what SIDE-GT-NDGP measured numerically:
`NC` for a triangle that must be real, and `0 < ...` for a configuration the engine reads from the figure.
-/

noncomputable section

namespace GeoCert

macro "pn" : tactic => `(tactic| (simp only [cr, dt, d2]; ring1))

theorem sum_sq_zero {X Y : ℝ} (h : X ^ 2 + Y ^ 2 = 0) : X = 0 ∧ Y = 0 := by
  have h1 : 0 ≤ X ^ 2 := sq_nonneg _
  have h2 : 0 ≤ Y ^ 2 := sq_nonneg _
  have h3 : X ^ 2 = 0 := by linarith
  have h4 : Y ^ 2 = 0 := by linarith
  exact ⟨by simpa using h3, by simpa using h4⟩

/-- a, b, c are not on one line -/
def NC (a b c : P) : Prop := cr a b a c ≠ 0

theorem NC.swap23 {a b c : P} (h : NC a b c) : NC a c b := by
  intro e
  apply h
  linear_combination (norm := pn) (-1 : ℝ) * e

theorem NC.swap12 {a b c : P} (h : NC a b c) : NC b a c := by
  intro e
  apply h
  linear_combination (norm := pn) (-1 : ℝ) * e

/-- a, b, c on one line, as `coll a b c` -/
abbrev Coll (a b c : P) : Prop := Para a b a c

/-- m is the midpoint of ab -/
def Midp (m a b : P) : Prop := 2 * m.x = a.x + b.x ∧ 2 * m.y = a.y + b.y

def SqCong (a b c d : P) : Prop := d2 a b - d2 c d = 0
def SqPerp (a b c d : P) : Prop := d2 a c - d2 a d - d2 b c + d2 b d = 0
def SqMid (m a b : P) : Prop := d2 a b - 4 * d2 m a = 0
def SqMedian (x m a b : P) : Prop := 2 * d2 x m + 2 * d2 m a - d2 x a - d2 x b = 0

/-! ## Lines -/

theorem coll_self1 (a b : P) : Coll a b a := by unfold Coll Para; pn
theorem coll_self2 (a b : P) : Coll a b b := by unfold Coll Para; pn

/-- a point of line ab, by its parameter -/
theorem coll_param {a b x : P} (hab : a ≠ b) (h : Coll a b x) :
    ∃ t : ℝ, x.x = a.x + t * (b.x - a.x) ∧ x.y = a.y + t * (b.y - a.y) := by
  have hp := d2_pos hab
  unfold Coll Para at h
  refine ⟨dt a b a x / d2 a b, ?_, ?_⟩
  · field_simp
    linear_combination (norm := pn) (-(b.y - a.y)) * h
  · field_simp
    linear_combination (norm := pn) (b.x - a.x) * h

/-- any two lines through points of line ab are parallel: the rule `line`, and a collinear fact read for any of its points -/
theorem para_of_line {a b x y z w : P} (hab : a ≠ b) (h1 : Coll a b x) (h2 : Coll a b y) (h3 : Coll a b z) (h4 : Coll a b w) : Para x y z w := by
  obtain ⟨t1, e1, f1⟩ := coll_param hab h1
  obtain ⟨t2, e2, f2⟩ := coll_param hab h2
  obtain ⟨t3, e3, f3⟩ := coll_param hab h3
  obtain ⟨t4, e4, f4⟩ := coll_param hab h4
  unfold Para cr
  rw [e1, e2, e3, e4, f1, f2, f3, f4]
  ring

/-- a point on line st, with s and t on line pq, is on line pq -/
theorem coll_ext {p q s t r : P} (hpq : p ≠ q) (hst : s ≠ t) (h1 : Coll p q s) (h2 : Coll p q t) (h3 : Coll s t r) : Coll p q r := by
  obtain ⟨t1, e1, f1⟩ := coll_param hpq h1
  obtain ⟨t2, e2, f2⟩ := coll_param hpq h2
  obtain ⟨t3, e3, f3⟩ := coll_param hst h3
  unfold Coll Para cr
  rw [e3, f3, e2, f2, e1, f1]
  ring

/-! ## Midpoints -/

theorem midp_of {m a b : P} (hab : a ≠ b) (c : Coll m a b) (h : Cong m a m b) : Midp m a b := by
  have hp := d2_pos hab
  unfold Coll Para at c
  unfold Cong at h
  have key : ((a.x + b.x - 2 * m.x) ^ 2 + (a.y + b.y - 2 * m.y) ^ 2) * d2 a b = 0 := by
    linear_combination (norm := pn) (d2 m a - d2 m b) * h + 4 * (cr m a m b) * c
  obtain ⟨z1, z2⟩ := sum_sq_zero ((mul_eq_zero.mp key).resolve_right hp.ne')
  exact ⟨by linarith, by linarith⟩

theorem Midp.x {m a b : P} (h : Midp m a b) : m.x = (a.x + b.x) / 2 := by have := h.1; linarith
theorem Midp.y {m a b : P} (h : Midp m a b) : m.y = (a.y + b.y) / 2 := by have := h.2; linarith

theorem Midp.coll {m a b : P} (h : Midp m a b) : Coll a b m := by
  unfold Coll Para cr
  rw [h.x, h.y]
  ring

theorem Midp.cong {m a b : P} (h : Midp m a b) : Cong m a m b := by
  unfold Cong d2
  rw [h.x, h.y]
  ring

theorem midp_half {m a b : P} (h : Midp m a b) : Half a b m a := by
  unfold Half d2
  rw [h.x, h.y]
  ring

theorem midline {m n a b c : P} (h : Midp m a b) (g : Midp n a c) : Para m n b c := by
  unfold Para cr
  rw [h.x, h.y, g.x, g.y]
  ring

theorem parallelogram1 {m a b c e : P} (h : Midp m a b) (g : Midp m c e) : Para a c b e := by
  have h1 := h.1; have h2 := h.2; have g1 := g.1; have g2 := g.2
  have ex : e.x = a.x + b.x - c.x := by linarith
  have ey : e.y = a.y + b.y - c.y := by linarith
  unfold Para cr
  rw [ex, ey]
  ring

theorem parallelogram2 {m a b c e : P} (h : Midp m a b) (g : Midp m c e) : Para a e b c := by
  have h1 := h.1; have h2 := h.2; have g1 := g.1; have g2 := g.2
  have cx : c.x = a.x + b.x - e.x := by linarith
  have cy : c.y = a.y + b.y - e.y := by linarith
  unfold Para cr
  rw [cx, cy]
  ring

/-- the fourth point of a parallelogram: with Para a c b e and Para a e b c, the diagonals bisect each other -/
theorem parallelogram_mid {m a b c e : P} (n : NC a b c) (h : Midp m a b) (p1 : Para a c b e) (p2 : Para a e b c) : Midp m c e := by
  unfold Para at p1 p2
  unfold NC at n
  have h1 := h.1; have h2 := h.2
  have kx : cr a b a c * (e.x - (a.x + b.x - c.x)) = 0 := by
    linear_combination (norm := pn) (c.x - a.x) * p2 + ((c.x - a.x) - (b.x - a.x)) * p1
  have ky : cr a b a c * (e.y - (a.y + b.y - c.y)) = 0 := by
    linear_combination (norm := pn) (c.y - a.y) * p2 + ((c.y - a.y) - (b.y - a.y)) * p1
  have ex := (mul_eq_zero.mp kx).resolve_left n
  have ey := (mul_eq_zero.mp ky).resolve_left n
  exact ⟨by linarith, by linarith⟩

theorem right_median {m a b c : P} (h : Midp m a b) (p : Perp a c c b) : Cong m a m c := by
  unfold Perp dt at p
  unfold Cong d2
  rw [h.x, h.y]
  linear_combination p

theorem mid_perp {m a b x : P} (h : Midp m a b) (p : Perp x m a b) : Cong x a x b := by
  unfold Perp dt at p
  unfold Cong d2
  rw [h.x, h.y] at p
  linear_combination (-2 : ℝ) * p

theorem chord_mid {o m a b : P} (h : Cong o a o b) (p : Perp o m a b) : Cong m a m b := by
  unfold Perp at p
  unfold Cong at h ⊢
  linear_combination (norm := pn) h + (2 : ℝ) * p

theorem sqmid {m a b : P} (h : Midp m a b) : SqMid m a b := by
  unfold SqMid d2
  rw [h.x, h.y]
  ring

theorem sqmedian {x m a b : P} (h : Midp m a b) : SqMedian x m a b := by
  unfold SqMedian d2
  rw [h.x, h.y]
  ring

/-! ## Equal lengths and perpendiculars -/

theorem isos1 {o x y : P} (h : Cong o x o y) : EqA x y o x o y x y := by
  unfold Cong at h
  unfold EqA
  linear_combination (norm := pn) (cr x y o x) * h

theorem isos2 {o x y : P} (h : Cong o x o y) : EqA x y o y o x x y := by
  unfold Cong at h
  unfold EqA
  linear_combination (norm := pn) (cr x y o x) * h

theorem base1 {o x y : P} (n : NC o x y) (h : EqA x y o x o y x y) : Cong o x o y := by
  unfold EqA at h
  unfold NC at n
  unfold Cong
  have k : cr o x o y * (d2 o x - d2 o y) = 0 := by linear_combination (norm := pn) (-1 : ℝ) * h
  have := (mul_eq_zero.mp k).resolve_left n
  linarith

theorem base2 {o x y : P} (n : NC o x y) (h : EqA x y o y o x x y) : Cong o x o y := by
  unfold EqA at h
  unfold NC at n
  unfold Cong
  have k : cr o x o y * (d2 o x - d2 o y) = 0 := by linear_combination (norm := pn) (-1 : ℝ) * h
  have := (mul_eq_zero.mp k).resolve_left n
  linarith

theorem perp_bisector {p q a b : P} (h1 : Cong p a p b) (h2 : Cong q a q b) : Perp a b p q := by
  unfold Cong at h1 h2
  unfold Perp
  linear_combination (norm := pn) (-1 / 2 : ℝ) * h1 + (1 / 2 : ℝ) * h2

theorem pyth_to {a b c d : P} (h : Perp a b c d) : SqPerp a b c d := by
  unfold Perp at h
  unfold SqPerp
  linear_combination (norm := pn) (-2 : ℝ) * h

theorem pyth_of {a b c d : P} (h : SqPerp a b c d) : Perp a b c d := by
  unfold SqPerp at h
  unfold Perp
  linear_combination (norm := pn) (-1 / 2 : ℝ) * h

theorem sqcong_to {a b c d : P} (h : Cong a b c d) : SqCong a b c d := by
  unfold Cong at h
  unfold SqCong
  linarith

theorem sqcong_of {a b c d : P} (h : SqCong a b c d) : Cong a b c d := by
  unfold SqCong at h
  unfold Cong
  linarith

end GeoCert
