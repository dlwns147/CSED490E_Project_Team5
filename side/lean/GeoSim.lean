import GeoRules

/-!
# Similar triangles, bisectors and the two ratio rules

`Sim` is a similarity that keeps orientation, `Sim2` one that reverses it. Two directed angles give a similar pair on any real triangle. Equal ratios alone do not: the engine reads the orientation
from its figure, and here that reading is the hypothesis `Read`. The same holds for `thales` and `trapezoid`, whose reading says two points fall on the same side.
-/

noncomputable section

namespace GeoCert

/-- pqr is carried onto abc by z ↦ (l + i m) z + const -/
def Sim (a b c p q r : P) : Prop := ∃ l m : ℝ,
  b.x - a.x = l * (q.x - p.x) - m * (q.y - p.y) ∧ b.y - a.y = l * (q.y - p.y) + m * (q.x - p.x) ∧
  c.x - a.x = l * (r.x - p.x) - m * (r.y - p.y) ∧ c.y - a.y = l * (r.y - p.y) + m * (r.x - p.x)

/-- the mirror image -/
def rf (p : P) : P := ⟨p.x, -p.y⟩

theorem rf_ne {p q : P} (h : p ≠ q) : rf p ≠ rf q := by
  intro e
  apply h
  have h1 := congrArg P.x e
  have h2 := congrArg P.y e
  simp [rf] at h1 h2
  ext <;> linarith

theorem d2_rf (p q : P) : d2 (rf p) (rf q) = d2 p q := by
  unfold d2 rf
  ring

/-- pqr reversed is carried onto abc -/
def Sim2 (a b c p q r : P) : Prop := Sim a b c (rf p) (rf q) (rf r)

/-- the triangles abc and pqr have the same orientation -/
def Read (a b c p q r : P) : Prop := 0 < cr a b a c * cr p q p r
/-- they have opposite orientations -/
def Read2 (a b c p q r : P) : Prop := cr a b a c * cr p q p r < 0

theorem Read.p12 {a b c p q r : P} (h : Read a b c p q r) : Read b a c q p r := by
  unfold Read at *
  have e : cr b a b c * cr q p q r = cr a b a c * cr p q p r := by pn
  rw [e]
  exact h

theorem Read.p23 {a b c p q r : P} (h : Read a b c p q r) : Read a c b p r q := by
  unfold Read at *
  have e : cr a c a b * cr p r p q = cr a b a c * cr p q p r := by pn
  rw [e]
  exact h

theorem Read2.p12 {a b c p q r : P} (h : Read2 a b c p q r) : Read2 b a c q p r := by
  unfold Read2 at *
  have e : cr b a b c * cr q p q r = cr a b a c * cr p q p r := by pn
  rw [e]
  exact h

theorem Read2.p23 {a b c p q r : P} (h : Read2 a b c p q r) : Read2 a c b p r q := by
  unfold Read2 at *
  have e : cr a c a b * cr p r p q = cr a b a c * cr p q p r := by pn
  rw [e]
  exact h

theorem Read2.rf {a b c p q r : P} (h : Read2 a b c p q r) : Read a b c (rf p) (rf q) (rf r) := by
  unfold Read2 at h
  unfold Read
  have e : cr a b a c * cr (GeoCert.rf p) (GeoCert.rf q) (GeoCert.rf p) (GeoCert.rf r) = - (cr a b a c * cr p q p r) := by
    simp only [cr, GeoCert.rf]
    ring
  rw [e]
  linarith

/-- an angle read on the mirror image: `EqA` of a pair with p q r s becomes the same with their mirror images in the other order -/
theorem eqa_rf {a b c d p q r s : P} (h : EqA a b c d p q r s) : EqA a b c d (rf r) (rf s) (rf p) (rf q) := by
  unfold EqA at *
  linear_combination (norm := (simp only [cr, dt, rf]; ring1)) h

theorem Sim.p23 {a b c p q r : P} (h : Sim a b c p q r) : Sim a c b p r q := by
  obtain ⟨l, m, e1, e2, e3, e4⟩ := h
  exact ⟨l, m, e3, e4, e1, e2⟩

theorem Sim.p12 {a b c p q r : P} (h : Sim a b c p q r) : Sim b a c q p r := by
  obtain ⟨l, m, e1, e2, e3, e4⟩ := h
  refine ⟨l, m, ?_, ?_, ?_, ?_⟩
  · linear_combination (-1 : ℝ) * e1
  · linear_combination (-1 : ℝ) * e2
  · linear_combination e3 - e1
  · linear_combination e4 - e2

theorem sim_eqa1 {a b c p q r : P} (h : Sim a b c p q r) : EqA a b a c p q p r := by
  obtain ⟨l, m, e1, e2, e3, e4⟩ := h
  have f1 : b.x = a.x + (l * (q.x - p.x) - m * (q.y - p.y)) := by linarith
  have f2 : b.y = a.y + (l * (q.y - p.y) + m * (q.x - p.x)) := by linarith
  have f3 : c.x = a.x + (l * (r.x - p.x) - m * (r.y - p.y)) := by linarith
  have f4 : c.y = a.y + (l * (r.y - p.y) + m * (r.x - p.x)) := by linarith
  unfold EqA dt cr
  rw [f1, f2, f3, f4]
  ring

theorem sim_r2 {a b c p q r : P} (h : Sim a b c p q r) : Ratio a b p q c a r p := by
  obtain ⟨l, m, e1, e2, e3, e4⟩ := h
  have f1 : b.x = a.x + (l * (q.x - p.x) - m * (q.y - p.y)) := by linarith
  have f2 : b.y = a.y + (l * (q.y - p.y) + m * (q.x - p.x)) := by linarith
  have f3 : c.x = a.x + (l * (r.x - p.x) - m * (r.y - p.y)) := by linarith
  have f4 : c.y = a.y + (l * (r.y - p.y) + m * (r.x - p.x)) := by linarith
  unfold Ratio d2
  rw [f1, f2, f3, f4]
  ring

theorem sim_r1 {a b c p q r : P} (h : Sim a b c p q r) : Ratio a b p q b c q r := by
  obtain ⟨l, m, e1, e2, e3, e4⟩ := h
  have f1 : b.x = a.x + (l * (q.x - p.x) - m * (q.y - p.y)) := by linarith
  have f2 : b.y = a.y + (l * (q.y - p.y) + m * (q.x - p.x)) := by linarith
  have f3 : c.x = a.x + (l * (r.x - p.x) - m * (r.y - p.y)) := by linarith
  have f4 : c.y = a.y + (l * (r.y - p.y) + m * (r.x - p.x)) := by linarith
  unfold Ratio d2
  rw [f1, f2, f3, f4]
  ring

theorem sim_eqa2 {a b c p q r : P} (h : Sim a b c p q r) : EqA b a b c q p q r := sim_eqa1 h.p12

/-- the two scaled equalities E1, E2 make a similarity -/
theorem sim_of_E {a b c p q r : P} (hab : a ≠ b) (hpq : p ≠ q)
    (E1 : d2 p q * dt a b a c = d2 a b * dt p q p r) (E2 : d2 p q * cr a b a c = d2 a b * cr p q p r) : Sim a b c p q r := by
  have hL := d2_pos hab
  have hM := d2_pos hpq
  refine ⟨dt p q a b / d2 p q, cr p q a b / d2 p q, ?_, ?_, ?_, ?_⟩
  · rw [div_mul_eq_mul_div, div_mul_eq_mul_div, ← sub_div, eq_div_iff hM.ne']
    simp only [cr, dt, d2]
    ring
  · rw [div_mul_eq_mul_div, div_mul_eq_mul_div, ← add_div, eq_div_iff hM.ne']
    simp only [cr, dt, d2]
    ring
  · rw [div_mul_eq_mul_div, div_mul_eq_mul_div, ← sub_div, eq_div_iff hM.ne']
    have k : d2 a b * ((c.x - a.x) * d2 p q - (dt p q a b * (r.x - p.x) - cr p q a b * (r.y - p.y))) = 0 := by
      linear_combination (norm := pn) (b.x - a.x) * E1 - (b.y - a.y) * E2
    have := (mul_eq_zero.mp k).resolve_left hL.ne'
    linarith
  · rw [div_mul_eq_mul_div, div_mul_eq_mul_div, ← add_div, eq_div_iff hM.ne']
    have k : d2 a b * ((c.y - a.y) * d2 p q - (dt p q a b * (r.y - p.y) + cr p q a b * (r.x - p.x))) = 0 := by
      linear_combination (norm := pn) (b.y - a.y) * E1 + (b.x - a.x) * E2
    have := (mul_eq_zero.mp k).resolve_left hL.ne'
    linarith

/-- two directed angles: no reading -/
theorem sim_aa {a b c p q r : P} (hab : a ≠ b) (hpq : p ≠ q) (n : NC a b c)
    (A : EqA a b a c p q p r) (B : EqA b a b c q p q r) : Sim a b c p q r := by
  unfold EqA at A B
  unfold NC at n
  have E2 : d2 p q * cr a b a c = d2 a b * cr p q p r := by
    linear_combination (norm := pn) B - A
  have k : cr a b a c * (d2 p q * dt a b a c - d2 a b * dt p q p r) = 0 := by
    linear_combination (norm := pn) (dt a b a c) * E2 + (d2 a b) * A
  have E1 := (mul_eq_zero.mp k).resolve_left n
  exact sim_of_E hab hpq (by linarith) E2

/-- three ratios, with the orientation read -/
theorem sim_sss {a b c p q r : P} (hab : a ≠ b) (hpq : p ≠ q) (rd : Read a b c p q r)
    (R1 : Ratio a b p q b c q r) (R2 : Ratio a b p q c a r p) : Sim a b c p q r := by
  unfold Ratio at R1 R2
  unfold Read at rd
  have hL := d2_pos hab
  have hM := d2_pos hpq
  have E1 : d2 p q * dt a b a c - d2 a b * dt p q p r = 0 := by
    linear_combination (norm := pn) (1 / 2 : ℝ) * R1 - (1 / 2 : ℝ) * R2
  have k : (d2 p q * cr a b a c - d2 a b * cr p q p r) * (d2 p q * cr a b a c + d2 a b * cr p q p r) = 0 := by
    linear_combination (norm := pn) (- d2 a b * d2 p q) * R2 - (d2 p q * dt a b a c + d2 a b * dt p q p r) * E1
  have s : d2 p q * cr a b a c + d2 a b * cr p q p r ≠ 0 := by
    intro e
    have h1 : (d2 p q * cr a b a c + d2 a b * cr p q p r) * cr p q p r = 0 := by rw [e]; ring
    have h2 : 0 < d2 p q * (cr a b a c * cr p q p r) := mul_pos hM rd
    have h3 : 0 ≤ d2 a b * (cr p q p r) ^ 2 := mul_nonneg hL.le (sq_nonneg _)
    nlinarith
  have E2 := (mul_eq_zero.mp k).resolve_right s
  exact sim_of_E hab hpq (by linarith) (by linarith)

theorem aux_sas {p q p' q' : ℝ} (h1 : p ^ 2 + q ^ 2 = p' ^ 2 + q' ^ 2) (h2 : q * p' = p * q') (hp : 0 < p * p') : p = p' ∧ q = q' := by
  have n' : p' ≠ 0 := by
    intro e
    rw [e] at hp
    simp at hp
  have key : (p ^ 2 - p' ^ 2) * (p' ^ 2 + q' ^ 2) = 0 := by
    linear_combination p' ^ 2 * h1 - (p * q' + q * p') * h2
  have pos : 0 < p' ^ 2 + q' ^ 2 := by
    have : 0 < p' ^ 2 := by positivity
    have := sq_nonneg q'
    linarith
  have d := (mul_eq_zero.mp key).resolve_right pos.ne'
  have f : (p - p') * (p + p') = 0 := by linear_combination d
  have s : p + p' ≠ 0 := by
    intro e
    have : p = -p' := by linarith
    rw [this] at hp
    nlinarith [sq_nonneg p']
  have e1 : p = p' := by
    have := (mul_eq_zero.mp f).resolve_right s
    linarith
  refine ⟨e1, ?_⟩
  have g : (q - q') * p' = 0 := by rw [← e1] at h2 ⊢; linear_combination h2
  have := (mul_eq_zero.mp g).resolve_right n'
  linarith

/-- two sides and the directed angle between them, at a, with the orientation read -/
theorem sim_sas {a b c p q r : P} (hab : a ≠ b) (hpq : p ≠ q) (rd : Read a b c p q r)
    (R : Ratio a b p q c a r p) (A : EqA a b a c p q p r) : Sim a b c p q r := by
  unfold Ratio at R
  unfold EqA at A
  unfold Read at rd
  have hL := d2_pos hab
  have hM := d2_pos hpq
  have i1 : (cr a b a c) ^ 2 + (dt a b a c) ^ 2 = d2 a b * d2 c a := by pn
  have i2 : (cr p q p r) ^ 2 + (dt p q p r) ^ 2 = d2 p q * d2 r p := by pn
  obtain ⟨E2, E1⟩ := aux_sas (p := d2 p q * cr a b a c) (q := d2 p q * dt a b a c) (p' := d2 a b * cr p q p r) (q' := d2 a b * dt p q p r)
    (by linear_combination (d2 p q) ^ 2 * i1 - (d2 a b) ^ 2 * i2 - (d2 a b * d2 p q) * R)
    (by linear_combination (d2 a b * d2 p q) * A)
    (by
      have : d2 p q * cr a b a c * (d2 a b * cr p q p r) = (d2 a b * d2 p q) * (cr a b a c * cr p q p r) := by ring
      rw [this]
      exact mul_pos (mul_pos hL hM) rd)
  exact sim_of_E hab hpq E1 E2

/-! ## Consequences of a similar pair with reversed orientation -/

theorem sim2_eqa1 {a b c p q r : P} (h : Sim2 a b c p q r) : EqA a b a c p r p q := by
  have k := sim_eqa1 h
  unfold EqA at *
  linear_combination (norm := (simp only [cr, dt, rf]; ring1)) k

theorem sim2_eqa2 {a b c p q r : P} (h : Sim2 a b c p q r) : EqA b a b c q r q p := by
  have k := sim_eqa2 h
  unfold EqA at *
  linear_combination (norm := (simp only [cr, dt, rf]; ring1)) k

theorem sim2_r1 {a b c p q r : P} (h : Sim2 a b c p q r) : Ratio a b p q b c q r := by
  have k := sim_r1 h
  unfold Ratio at *
  simpa only [d2_rf] using k

theorem sim2_r2 {a b c p q r : P} (h : Sim2 a b c p q r) : Ratio a b p q c a r p := by
  have k := sim_r2 h
  unfold Ratio at *
  simpa only [d2_rf] using k

theorem ratio_rf {a b c d e f g h : P} (k : Ratio a b c d e f g h) : Ratio a b (rf c) (rf d) e f (rf g) (rf h) := by
  unfold Ratio at *
  simpa only [d2_rf] using k

/-! ## The bisector -/

theorem coll_rot {e b c : P} (h : Coll e b c) : Coll b c e := by
  unfold Coll Para at *
  linear_combination (norm := pn) h

set_option maxHeartbeats 2000000 in
theorem bisector_id {a b c e : P} (t : ℝ) (e1 : e.x = b.x + t * (c.x - b.x)) (e2 : e.y = b.y + t * (c.y - b.y)) :
    d2 b c * (dt a b a e * cr a e a c - cr a b a e * dt a e a c) = cr a b a c * (d2 e c * d2 a b - d2 e b * d2 a c) := by
  unfold cr dt d2
  rw [e1, e2]
  ring

/-- the foot of a bisector, inner or outer, from equal ratios: directed angles modulo π do not tell the two apart -/
theorem bisector_A {a b c e : P} (hbc : b ≠ c) (co : Coll e b c) (R : Ratio e b e c a b a c) : EqA a b a e a e a c := by
  obtain ⟨t, e1, e2⟩ := coll_param hbc (coll_rot co)
  have k := bisector_id (a := a) t e1 e2
  unfold Ratio at R
  unfold EqA
  have hs := d2_pos hbc
  rw [R] at k
  have z : d2 b c * (dt a b a e * cr a e a c - cr a b a e * dt a e a c) = 0 := by rw [k]; ring
  exact (mul_eq_zero.mp z).resolve_left hs.ne'

theorem bisector_R {a b c e : P} (hbc : b ≠ c) (n : NC a b c) (co : Coll e b c) (A : EqA a b a e a e a c) : Ratio e b e c a b a c := by
  obtain ⟨t, e1, e2⟩ := coll_param hbc (coll_rot co)
  have k := bisector_id (a := a) t e1 e2
  unfold EqA at A
  unfold Ratio
  unfold NC at n
  rw [A] at k
  have z : cr a b a c * (d2 e c * d2 a b - d2 e b * d2 a c) = 0 := by rw [← k]; ring
  have := (mul_eq_zero.mp z).resolve_left n
  linarith

/-! ## The two rules with a side read from the figure -/

/-- both of the points a, b lie on the same side of o with respect to c, e -/
def ReadT (o a c b e : P) : Prop := 0 < dt a o a c * dt b o b e

theorem thales {o a b c e : P} (hoa : o ≠ a) (hob : o ≠ b) (c1 : Coll o a c) (c2 : Coll o b e)
    (R : Ratio o a a c o b b e) (rd : ReadT o a c b e) : Para a b c e := by
  obtain ⟨p, f1, f2⟩ := coll_param hoa c1
  obtain ⟨q, g1, g2⟩ := coll_param hob c2
  have hA := d2_pos hoa
  have hB := d2_pos hob
  unfold Ratio at R
  unfold ReadT at rd
  have i1 : d2 a c = (p - 1) ^ 2 * d2 o a := by
    simp only [d2]
    rw [f1, f2]
    ring
  have i2 : d2 b e = (q - 1) ^ 2 * d2 o b := by
    simp only [d2]
    rw [g1, g2]
    ring
  have i3 : dt a o a c = -(p - 1) * d2 o a := by
    simp only [dt, d2]
    rw [f1, f2]
    ring
  have i4 : dt b o b e = -(q - 1) * d2 o b := by
    simp only [dt, d2]
    rw [g1, g2]
    ring
  rw [i1, i2] at R
  rw [i3, i4] at rd
  have k : (d2 o a * d2 o b) * ((q - 1) ^ 2 - (p - 1) ^ 2) = 0 := by linear_combination R
  have d := (mul_eq_zero.mp k).resolve_left (mul_pos hA hB).ne'
  have f : (q - p) * (q + p - 2) = 0 := by linear_combination d
  have s : 0 < (p - 1) * (q - 1) := by
    have e : -(p - 1) * d2 o a * (-(q - 1) * d2 o b) = ((p - 1) * (q - 1)) * (d2 o a * d2 o b) := by ring
    rw [e] at rd
    exact (pos_iff_pos_of_mul_pos rd).mpr (mul_pos hA hB)
  have s2 : q + p - 2 ≠ 0 := by
    intro e
    have : q - 1 = -(p - 1) := by linarith
    rw [this] at s
    nlinarith [sq_nonneg (p - 1)]
  have e : q - p = 0 := (mul_eq_zero.mp f).resolve_right s2
  have eq : q = p := by linarith
  unfold Para cr
  rw [f1, f2, g1, g2, eq]
  ring

/-- the ratio the trapezoid reads: m and k fall on the same side -/
def ReadZ (m a e k b c : P) : Prop := 0 < dt m a m e * dt k b k c

/-- a trapezoid abce, m on ae, k on bc -/
theorem trap_setup {a b c e m k : P} (hab : a ≠ b) (hae : a ≠ e) (hbc : b ≠ c) (pa : Para a b c e) (c1 : Coll m a e) (c2 : Coll k b c) :
    ∃ l s r : ℝ, e.x = c.x + l * (b.x - a.x) ∧ e.y = c.y + l * (b.y - a.y) ∧ m.x = a.x + s * (e.x - a.x) ∧ m.y = a.y + s * (e.y - a.y) ∧
      k.x = b.x + r * (c.x - b.x) ∧ k.y = b.y + r * (c.y - b.y) := by
  have hp := d2_pos hab
  unfold Para at pa
  have u1 := coll_param hae (coll_rot c1)
  have u2 := coll_param hbc (coll_rot c2)
  obtain ⟨s, s1, s2⟩ := u1
  obtain ⟨r, r1, r2⟩ := u2
  refine ⟨dt a b c e / d2 a b, s, r, ?_, ?_, s1, s2, r1, r2⟩
  · have : (e.x - c.x) * d2 a b = dt a b c e * (b.x - a.x) := by
      linear_combination (norm := pn) (-(b.y - a.y)) * pa
    field_simp
    linarith
  · have : (e.y - c.y) * d2 a b = dt a b c e * (b.y - a.y) := by
      linear_combination (norm := pn) (b.x - a.x) * pa
    field_simp
    linarith

theorem trap_core {a b c e m k : P} {l s r : ℝ} (n : NC a b c) (he1 : e.x = c.x + l * (b.x - a.x)) (he2 : e.y = c.y + l * (b.y - a.y))
    (hm1 : m.x = a.x + s * (e.x - a.x)) (hm2 : m.y = a.y + s * (e.y - a.y)) (hk1 : k.x = b.x + r * (c.x - b.x)) (hk2 : k.y = b.y + r * (c.y - b.y)) :
    Para m k a b ↔ r = s := by
  unfold NC at n
  have id : cr m k a b = (s - r) * cr a b a c := by
    simp only [cr]
    rw [hm1, hm2, hk1, hk2, he1, he2]
    ring
  unfold Para
  rw [id]
  constructor
  · intro h
    have := (mul_eq_zero.mp h).resolve_right n
    linarith
  · intro h
    rw [h]
    ring

theorem trap_R {a b c e m k : P} (hab : a ≠ b) (hae : a ≠ e) (hbc : b ≠ c) (n : NC a b c) (pa : Para a b c e)
    (c1 : Coll m a e) (c2 : Coll k b c) (q : Para m k a b) : Ratio m a m e k b k c := by
  obtain ⟨l, s, r, he1, he2, hm1, hm2, hk1, hk2⟩ := trap_setup hab hae hbc pa c1 c2
  have e := (trap_core n he1 he2 hm1 hm2 hk1 hk2).mp q
  unfold Ratio d2
  rw [hm1, hm2, hk1, hk2, e]
  ring

theorem trap_Q {a b c e m k : P} (hab : a ≠ b) (hae : a ≠ e) (hbc : b ≠ c) (n : NC a b c) (pa : Para a b c e)
    (c1 : Coll m a e) (c2 : Coll k b c) (R : Ratio m a m e k b k c) (rd : ReadZ m a e k b c) : Para m k a b := by
  obtain ⟨l, s, r, he1, he2, hm1, hm2, hk1, hk2⟩ := trap_setup hab hae hbc pa c1 c2
  refine (trap_core n he1 he2 hm1 hm2 hk1 hk2).mpr ?_
  have hF := d2_pos hae
  have hG := d2_pos hbc
  have i1 : d2 m a = s ^ 2 * d2 a e := by simp only [d2]; rw [hm1, hm2]; ring
  have i2 : d2 m e = (1 - s) ^ 2 * d2 a e := by simp only [d2]; rw [hm1, hm2]; ring
  have i3 : d2 k b = r ^ 2 * d2 b c := by simp only [d2]; rw [hk1, hk2]; ring
  have i4 : d2 k c = (1 - r) ^ 2 * d2 b c := by simp only [d2]; rw [hk1, hk2]; ring
  have i5 : dt m a m e = -(s * (1 - s)) * d2 a e := by simp only [dt, d2]; rw [hm1, hm2]; ring
  have i6 : dt k b k c = -(r * (1 - r)) * d2 b c := by simp only [dt, d2]; rw [hk1, hk2]; ring
  unfold Ratio at R
  unfold ReadZ at rd
  rw [i1, i2, i3, i4] at R
  rw [i5, i6] at rd
  have key : (d2 a e * d2 b c) * ((s * (1 - r)) ^ 2 - ((1 - s) * r) ^ 2) = 0 := by linear_combination R
  have d := (mul_eq_zero.mp key).resolve_left (mul_pos hF hG).ne'
  have f : (s - r) * (s + r - 2 * r * s) = 0 := by linear_combination d
  have sg : 0 < (s * (1 - s)) * (r * (1 - r)) := by
    have e : -(s * (1 - s)) * d2 a e * (-(r * (1 - r)) * d2 b c) = ((s * (1 - s)) * (r * (1 - r))) * (d2 a e * d2 b c) := by ring
    rw [e] at rd
    exact (pos_iff_pos_of_mul_pos rd).mpr (mul_pos hF hG)
  have s2 : s + r - 2 * r * s ≠ 0 := by
    intro e
    have : s * (1 - r) = -(r * (1 - s)) := by linarith
    have h3 : (s * (1 - r)) * (r * (1 - s)) = (s * (1 - s)) * (r * (1 - r)) := by ring
    rw [this] at h3
    nlinarith [sq_nonneg (r * (1 - s))]
  have := (mul_eq_zero.mp f).resolve_right s2
  linarith

end GeoCert
