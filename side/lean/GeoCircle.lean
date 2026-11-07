import GeoSim

/-!
# Circles

A circle of the engine is a group of points with a variable t for each: a chord xy has the direction t(x) + t(y), and the radius to x the direction 2 t(x) + π/2. Here t is a real function of the point,
defined from the centre and the radius, and the two relations are theorems. The engine's groups become a centre and a squared radius.
-/

noncomputable section
open Complex

namespace GeoCert

/-- x lies on the circle with centre o and squared radius r -/
def On (o : P) (r : ℝ) (x : P) : Prop := d2 o x = r

theorem normSq_zc (a b : P) : Complex.normSq (zc a b) = d2 a b := by
  simp [zc, Complex.normSq_apply, d2]
  ring

theorem zc_sub (o x y : P) : zc x y = zc o y - zc o x := by
  apply Complex.ext <;> simp [zc]

theorem mul_conj_zc (a b : P) : zc a b * (starRingEnd ℂ) (zc a b) = ((d2 a b : ℝ) : ℂ) := by
  rw [Complex.mul_conj, normSq_zc]

/-- the point of the circle as a unit complex number, turned by a quarter -/
def uz (o : P) (r : ℝ) (x : P) : ℂ := I * zc o x / ((Real.sqrt r : ℝ) : ℂ)

/-- the variable of a point on a circle -/
def tz (o : P) (r : ℝ) (x : P) : ℝ := Complex.arg (uz o r x) / 2

theorem sqrt_sq_c {r : ℝ} (hr : 0 < r) : ((Real.sqrt r : ℝ) : ℂ) * ((Real.sqrt r : ℝ) : ℂ) = (r : ℂ) := by
  rw [← Complex.ofReal_mul, Real.mul_self_sqrt hr.le]

theorem sqrt_ne_c {r : ℝ} (hr : 0 < r) : ((Real.sqrt r : ℝ) : ℂ) ≠ 0 := by
  have := Real.sqrt_pos.mpr hr
  exact_mod_cast this.ne'

theorem abs_uz {o x : P} {r : ℝ} (hr : 0 < r) (h : On o r x) : Complex.abs (uz o r x) = 1 := by
  unfold uz
  rw [map_div₀, map_mul, Complex.abs_I, one_mul, Complex.abs_ofReal, abs_of_pos (Real.sqrt_pos.mpr hr)]
  have : Complex.abs (zc o x) = Real.sqrt r := by
    rw [Complex.abs_apply, normSq_zc, h]
  rw [this]
  exact div_self (Real.sqrt_pos.mpr hr).ne'

theorem ee_tz {o x : P} {r : ℝ} (hr : 0 < r) (h : On o r x) : ee (tz o r x) = uz o r x := by
  have h1 := Complex.abs_mul_exp_arg_mul_I (uz o r x)
  rw [abs_uz hr h] at h1
  unfold ee tz
  simp only [Complex.ofReal_one, one_mul] at h1
  have : (((2 * (Complex.arg (uz o r x) / 2) : ℝ)) : ℂ) = ((Complex.arg (uz o r x) : ℝ) : ℂ) := by
    congr 1
    ring
  rw [this]
  exact h1

theorem zc_ne_of_on {o x : P} {r : ℝ} (hr : 0 < r) (h : On o r x) : zc o x ≠ 0 := by
  intro e
  have := normSq_zc o x
  rw [e, map_zero, h] at this
  linarith

theorem r_ne_c {r : ℝ} (hr : 0 < r) : (r : ℂ) ≠ 0 := by exact_mod_cast hr.ne'

theorem uz_mul {o x y : P} {r : ℝ} (hr : 0 < r) : uz o r x * uz o r y = -(zc o x * zc o y) / (r : ℂ) := by
  have s := sqrt_ne_c hr
  have ss := sqrt_sq_c hr
  have rc := r_ne_c hr
  unfold uz
  field_simp
  rw [ss]
  have : I * I = -1 := Complex.I_mul_I
  linear_combination (zc o x * zc o y * (r : ℂ)) * this

theorem uz_ne {o x : P} {r : ℝ} (hr : 0 < r) (hx : On o r x) : uz o r x ≠ 0 := by
  intro e
  have := abs_uz hr hx
  rw [e, map_zero] at this
  exact zero_ne_one this

/-- a chord: `u(x, y) = t(x) + t(y)` -/
theorem chord {o x y : P} {r : ℝ} (hr : 0 < r) (hx : On o r x) (hy : On o r y) (hxy : x ≠ y) : ModPi (U x y - tz o r x - tz o r y) := by
  rw [modPi_iff, ee_sub, ee_sub, ee_U hxy, ee_tz hr hx, ee_tz hr hy]
  have cd := conj_ne (zc_ne hxy)
  have rc := r_ne_c hr
  have px := mul_conj_zc o x
  have py := mul_conj_zc o y
  rw [show d2 o x = r from hx] at px
  rw [show d2 o y = r from hy] at py
  have key : dirc x y = uz o r x * uz o r y := by
    rw [uz_mul hr]
    unfold dirc
    rw [div_eq_iff cd, zc_sub o x y, map_sub]
    field_simp
    linear_combination (zc o x) * py - (zc o y) * px
  rw [key, div_div, div_self (mul_ne_zero (uz_ne hr hx) (uz_ne hr hy))]

/-- a radius: `u(o, x) = 2 t(x) + π/2` -/
theorem radius {o x : P} {r : ℝ} (hr : 0 < r) (hx : On o r x) (hox : o ≠ x) : ModPi (U o x - 2 * tz o r x - Real.pi / 2) := by
  have e : U o x - 2 * tz o r x - Real.pi / 2 = U o x - tz o r x - tz o r x - Real.pi / 2 := by ring
  rw [e, modPi_iff, ee_sub, ee_sub, ee_sub, ee_U hox, ee_tz hr hx, ee_half]
  have cd := conj_ne (zc_ne hox)
  have rc := r_ne_c hr
  have px := mul_conj_zc o x
  rw [show d2 o x = r from hx] at px
  have key : dirc o x = -(uz o r x * uz o r x) := by
    rw [uz_mul hr]
    unfold dirc
    rw [div_eq_iff cd]
    field_simp
    linear_combination (-(zc o x)) * px
  have u := uz_ne hr hx
  rw [key]
  field_simp

theorem d2_on {o x y : P} {r : ℝ} (hx : On o r x) (hy : On o r y) : Cong o x o y := by
  unfold Cong
  rw [show d2 o x = r from hx, show d2 o y = r from hy]

/-- three points of a circle are not on a line -/
theorem on_nc {o x y z : P} {r : ℝ} (hx : On o r x) (hy : On o r y) (hz : On o r z) (hxy : x ≠ y) (hxz : x ≠ z) (hyz : y ≠ z) : NC x y z := by
  intro e
  obtain ⟨t, f1, f2⟩ := coll_param hxy e
  have hp := d2_pos hxy
  have id : d2 o z = (1 - t) * d2 o x + t * d2 o y - t * (1 - t) * d2 x y := by
    simp only [d2]
    rw [f1, f2]
    ring
  rw [show d2 o x = r from hx, show d2 o y = r from hy, show d2 o z = r from hz] at id
  have k : t * (1 - t) * d2 x y = 0 := by linear_combination id
  have k2 := (mul_eq_zero.mp k).resolve_right hp.ne'
  rcases mul_eq_zero.mp k2 with h | h
  · apply hxz
    rw [h] at f1 f2
    ext <;> simp [f1, f2]
  · apply hyz
    have : t = 1 := by linarith
    rw [this] at f1 f2
    ext <;> simp [f1, f2]

/-- a circle is fixed by three points -/
theorem circ_eq {o o' x y z : P} {r r' : ℝ} (hx : On o r x) (hy : On o r y) (hz : On o r z)
    (gx : On o' r' x) (gy : On o' r' y) (gz : On o' r' z) (n : NC x y z) : o = o' ∧ r = r' := by
  have p1 : Perp x y o o' := perp_bisector (d2_on hx hy) (d2_on gx gy)
  have p2 : Perp x z o o' := perp_bisector (d2_on hx hz) (d2_on gx gz)
  unfold Perp at p1 p2
  unfold NC at n
  have k1 : cr x y x z * (o'.x - o.x) = 0 := by
    linear_combination (norm := pn) (z.y - x.y) * p1 - (y.y - x.y) * p2
  have k2 : cr x y x z * (o'.y - o.y) = 0 := by
    linear_combination (norm := pn) (y.x - x.x) * p2 - (z.x - x.x) * p1
  have e1 := (mul_eq_zero.mp k1).resolve_left n
  have e2 := (mul_eq_zero.mp k2).resolve_left n
  have eo : o = o' := by ext <;> linarith
  refine ⟨eo, ?_⟩
  rw [eo] at hx
  exact hx.symm.trans gx

/-- what lies on a circle with three points of another lies on the other -/
theorem On.move {o o' x y z p : P} {r r' : ℝ} (hx : On o r x) (hy : On o r y) (hz : On o r z)
    (gx : On o' r' x) (gy : On o' r' y) (gz : On o' r' z) (hxy : x ≠ y) (hxz : x ≠ z) (hyz : y ≠ z) (hp : On o' r' p) : On o r p := by
  obtain ⟨e1, e2⟩ := circ_eq hx hy hz gx gy gz (on_nc hx hy hz hxy hxz hyz)
  rw [e1, e2]
  exact hp

/-- a centre and a point give a circle -/
theorem on_centre {o x y : P} (h : Cong o x o y) : On o (d2 o x) y := h.symm

/-- the inscribed angle: equal directed angles on ab from x and y put the four points on one circle -/
theorem cyc_of_eqa {x a b y : P} (hxa : x ≠ a) (n : NC x a b) (h : EqA x a x b y a y b) :
    ∃ (o : P) (r : ℝ), 0 < r ∧ On o r x ∧ On o r a ∧ On o r b ∧ On o r y := by
  unfold NC at n
  unfold EqA at h
  set X := cr x a x b with hX
  set gx := (d2 x a * (b.y - x.y) - d2 x b * (a.y - x.y)) / (2 * X) with hgx
  set gy := (d2 x b * (a.x - x.x) - d2 x a * (b.x - x.x)) / (2 * X) with hgy
  have fx : 2 * X * gx = d2 x a * (b.y - x.y) - d2 x b * (a.y - x.y) := by
    rw [hgx]
    field_simp
  have fy : 2 * X * gy = d2 x b * (a.x - x.x) - d2 x a * (b.x - x.x) := by
    rw [hgy]
    field_simp
  have dd : ∀ p : P, d2 (⟨x.x + gx, x.y + gy⟩ : P) p - d2 (⟨x.x + gx, x.y + gy⟩ : P) x = d2 x p - 2 * ((p.x - x.x) * gx + (p.y - x.y) * gy) := by
    intro p
    simp only [d2]
    ring
  have ka : X * (d2 x a - 2 * ((a.x - x.x) * gx + (a.y - x.y) * gy)) = 0 := by
    linear_combination (norm := (simp only [hX, cr, d2]; ring1)) (-(a.x - x.x)) * fx - (a.y - x.y) * fy
  have kb : X * (d2 x b - 2 * ((b.x - x.x) * gx + (b.y - x.y) * gy)) = 0 := by
    linear_combination (norm := (simp only [hX, cr, d2]; ring1)) (-(b.x - x.x)) * fx - (b.y - x.y) * fy
  have ky : X * (d2 x y - 2 * ((y.x - x.x) * gx + (y.y - x.y) * gy)) = 0 := by
    linear_combination (norm := (simp only [hX, cr, dt, d2]; ring1)) (-(y.x - x.x)) * fx - (y.y - x.y) * fy - h
  have ea := (mul_eq_zero.mp ka).resolve_left n
  have eb := (mul_eq_zero.mp kb).resolve_left n
  have ey := (mul_eq_zero.mp ky).resolve_left n
  have oa := dd a
  have ob := dd b
  have oy := dd y
  rw [ea] at oa
  rw [eb] at ob
  rw [ey] at oy
  have hne : (⟨x.x + gx, x.y + gy⟩ : P) ≠ x := by
    intro e
    have hz : d2 (⟨x.x + gx, x.y + gy⟩ : P) x = 0 := by rw [e]; exact d2_self x
    rw [hz] at oa
    have h1 : d2 (⟨x.x + gx, x.y + gy⟩ : P) a = 0 := by linarith
    rw [e] at h1
    exact (d2_pos hxa).ne' h1
  refine ⟨⟨x.x + gx, x.y + gy⟩, d2 ⟨x.x + gx, x.y + gy⟩ x, d2_pos hne, rfl, ?_, ?_, ?_⟩
  · exact (sub_eq_zero.mp oa)
  · exact (sub_eq_zero.mp ob)
  · exact (sub_eq_zero.mp oy)

theorem normSq_sub_comm (p q : ℂ) : Complex.normSq (p - q) = Complex.normSq (q - p) := by
  rw [← neg_sub, Complex.normSq_neg]

theorem chords_eq {p q s t : ℂ} {r : ℝ} (hr : 0 < r) (hq : Complex.normSq q = r) (ht : Complex.normSq t = r) (e : p * t = q * s) :
    Complex.normSq (q - p) = Complex.normSq (t - s) := by
  have k : Complex.normSq t * Complex.normSq (q - p) = Complex.normSq q * Complex.normSq (t - s) := by
    rw [← map_mul, ← map_mul]
    congr 1
    linear_combination (-1 : ℂ) * e
  rw [ht, hq] at k
  exact mul_left_cancel₀ hr.ne' k

theorem uz_cancel {o a b c d : P} {r : ℝ} (hr : 0 < r) (e : uz o r a * uz o r d = uz o r b * uz o r c) : zc o a * zc o d = zc o b * zc o c := by
  rw [uz_mul hr, uz_mul hr] at e
  have rc := r_ne_c hr
  field_simp at e
  rcases e with e | e
  · exact e
  · exact absurd e hr.ne'

/-- equal differences of the variables give equal chords -/
theorem equal_chords1 {o a b c d : P} {r : ℝ} (hr : 0 < r) (ha : On o r a) (hb : On o r b) (hc : On o r c) (hd : On o r d)
    (h : ModPi (tz o r a - tz o r b - tz o r c + tz o r d)) : Cong a b c d := by
  rw [modPi_iff, ee_add, ee_sub, ee_sub, ee_tz hr ha, ee_tz hr hb, ee_tz hr hc, ee_tz hr hd] at h
  have nb := uz_ne hr hb
  have nc := uz_ne hr hc
  have e : uz o r a * uz o r d = uz o r b * uz o r c := by
    field_simp at h
    exact h
  have e2 := uz_cancel hr e
  unfold Cong
  rw [← normSq_zc a b, ← normSq_zc c d, zc_sub o a b, zc_sub o c d]
  exact chords_eq hr ((normSq_zc o b).trans hb) ((normSq_zc o d).trans hd) e2

theorem equal_chords2 {o a b c d : P} {r : ℝ} (hr : 0 < r) (ha : On o r a) (hb : On o r b) (hc : On o r c) (hd : On o r d)
    (h : ModPi (tz o r a - tz o r b + tz o r c - tz o r d)) : Cong a b c d := by
  have e0 : tz o r a - tz o r b + tz o r c - tz o r d = tz o r a - tz o r b - tz o r d + tz o r c := by ring
  rw [e0] at h
  have k := equal_chords1 hr ha hb hd hc h
  unfold Cong at *
  rw [k, d2_comm]

end GeoCert
