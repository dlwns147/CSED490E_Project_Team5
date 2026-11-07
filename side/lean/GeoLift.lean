import GeoCert

/-!
# Directions modulo 2π: a reading proved, not assumed

A row of the closure holds modulo π, which forgets which way a line points. Some rules know more. Two similar triangles, an isosceles triangle, a midpoint and a
radius give relations between directions of vectors `Th a b` modulo 2π, and the double of any row modulo π holds modulo 2π. If the relation a reading asks for is an
integer combination of these, the reading is a theorem and leaves the statement.
-/

noncomputable section
open Complex

namespace GeoCert

/-- the direction of the vector ab -/
def Th (a b : P) : ℝ := Complex.arg (zc a b)

/-- r is a multiple of 2π -/
def Mod2 (r : ℝ) : Prop := ∃ k : ℤ, r = 2 * k * Real.pi

/-- the isomorphism of ℝ modulo 2π with the unit circle -/
def e1 (t : ℝ) : ℂ := exp ((t : ℂ) * I)

theorem e1_add (s t : ℝ) : e1 (s + t) = e1 s * e1 t := by
  unfold e1
  rw [← Complex.exp_add]
  congr 1
  push_cast
  ring

theorem e1_sub (s t : ℝ) : e1 (s - t) = e1 s / e1 t := by
  unfold e1
  rw [← Complex.exp_sub]
  congr 1
  push_cast
  ring

theorem e1_ne (t : ℝ) : e1 t ≠ 0 := Complex.exp_ne_zero _

theorem e1_pi : e1 Real.pi = -1 := by
  unfold e1
  exact Complex.exp_pi_mul_I

theorem mod2_iff (r : ℝ) : Mod2 r ↔ e1 r = 1 := by
  unfold Mod2 e1
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
    linarith

theorem Mod2.add {r s : ℝ} (h : Mod2 r) (g : Mod2 s) : Mod2 (r + s) := by
  obtain ⟨k, hk⟩ := h
  obtain ⟨l, hl⟩ := g
  exact ⟨k + l, by rw [hk, hl]; push_cast; ring⟩

theorem Mod2.zmul {r : ℝ} (n : ℤ) (h : Mod2 r) : Mod2 ((n : ℝ) * r) := by
  obtain ⟨k, hk⟩ := h
  exact ⟨n * k, by rw [hk]; push_cast; ring⟩

theorem Mod2.int (n : ℤ) : Mod2 (2 * (n : ℝ) * Real.pi) := ⟨n, rfl⟩

theorem Mod2.congr {r s : ℝ} (e : r = s) (h : Mod2 r) : Mod2 s := e ▸ h

theorem Mod2.dbl {r : ℝ} (h : ModPi r) : Mod2 (2 * r) := by
  obtain ⟨k, hk⟩ := h
  exact ⟨k, by rw [hk]; ring⟩

theorem abs_c_ne {z : ℂ} (h : z ≠ 0) : ((Complex.abs z : ℝ) : ℂ) ≠ 0 := by
  simpa using h

theorem e1_arg {z : ℂ} (h : z ≠ 0) : e1 (Complex.arg z) = z / ((Complex.abs z : ℝ) : ℂ) := by
  have := Complex.abs_mul_exp_arg_mul_I z
  unfold e1
  rw [eq_div_iff (abs_c_ne h), mul_comm]
  exact this

/-- four vectors with z1 z4 a positive multiple of z2 z3 -/
theorem arg4 {z1 z2 z3 z4 : ℂ} (h1 : z1 ≠ 0) (h2 : z2 ≠ 0) (h3 : z3 ≠ 0) (h4 : z4 ≠ 0) {k : ℝ} (hk : 0 < k)
    (e : (k : ℂ) * (z1 * z4) = z2 * z3) : Mod2 (Complex.arg z1 - Complex.arg z2 - Complex.arg z3 + Complex.arg z4) := by
  rw [mod2_iff, e1_add, e1_sub, e1_sub, e1_arg h1, e1_arg h2, e1_arg h3, e1_arg h4]
  have n := congrArg Complex.abs e
  rw [map_mul, map_mul, map_mul, Complex.abs_ofReal, abs_of_pos hk] at n
  have nc : (k : ℂ) * (((Complex.abs z1 : ℝ) : ℂ) * ((Complex.abs z4 : ℝ) : ℂ)) = ((Complex.abs z2 : ℝ) : ℂ) * ((Complex.abs z3 : ℝ) : ℂ) := by
    exact_mod_cast n
  have c1 := abs_c_ne h1
  have c2 := abs_c_ne h2
  have c3 := abs_c_ne h3
  have c4 := abs_c_ne h4
  field_simp
  linear_combination ((Complex.abs z1 : ℝ) : ℂ) * ((Complex.abs z4 : ℝ) : ℂ) * e - z1 * z4 * nc

theorem arg2 {z1 z2 : ℂ} {k : ℝ} (hk : 0 < k) (e : (k : ℂ) * z1 = z2) : Mod2 (Complex.arg z1 - Complex.arg z2) := by
  rw [← e, Complex.arg_real_mul z1 hk]
  exact ⟨0, by simp⟩

theorem th_swap {a b : P} (h : a ≠ b) : Mod2 (Th b a - Th a b - Real.pi) := by
  unfold Th
  have z := zc_ne h
  have z' : zc b a ≠ 0 := by rw [zc_swap]; exact neg_ne_zero.mpr z
  rw [mod2_iff, e1_sub, e1_sub, e1_arg z, e1_arg z', e1_pi, zc_swap a b, map_neg_eq_map]
  have c := abs_c_ne z
  field_simp
  ring

theorem ee_th {a b : P} (h : a ≠ b) : ee (Th a b) = dirc a b := by
  have z := zc_ne h
  have e := e1_arg z
  have c := abs_c_ne z
  have ee2 : ee (Th a b) = e1 (Th a b) * e1 (Th a b) := by
    unfold ee e1
    rw [← Complex.exp_add]
    congr 1
    push_cast
    ring
  have m : zc a b * (starRingEnd ℂ) (zc a b) = ((Complex.abs (zc a b) : ℝ) : ℂ) * ((Complex.abs (zc a b) : ℝ) : ℂ) := by
    rw [Complex.mul_conj, Complex.normSq_eq_abs]
    push_cast
    ring
  rw [ee2]
  unfold Th dirc
  rw [e]
  have cz := conj_ne z
  field_simp
  linear_combination (zc a b) * m

theorem th_u {a b : P} (h : a ≠ b) : ModPi (Th a b - U a b) := by
  rw [modPi_iff, ee_sub, ee_th h, ee_U h]
  exact div_self (by
    have := ee_ne (U a b)
    rwa [ee_U h] at this)

theorem sim_w {a b c p q r : P} (s : Sim a b c p q r) : ∃ w : ℂ, zc a b = w * zc p q ∧ zc a c = w * zc p r := by
  obtain ⟨l, m, h1, h2, h3, h4⟩ := s
  refine ⟨⟨l, m⟩, ?_, ?_⟩
  · apply Complex.ext
    · simp [zc, Complex.mul_re]; linarith
    · simp [zc, Complex.mul_im]; linarith
  · apply Complex.ext
    · simp [zc, Complex.mul_re]; linarith
    · simp [zc, Complex.mul_im]; linarith

/-- two directly similar triangles have the same angle at a, modulo 2π -/
theorem sim_lift {a b c p q r : P} (s : Sim a b c p q r) (hab : a ≠ b) (hac : a ≠ c) (hpq : p ≠ q) (hpr : p ≠ r) :
    Mod2 (Th a b - Th a c - Th p q + Th p r) := by
  obtain ⟨w, e1', e2⟩ := sim_w s
  have := arg4 (k := 1) (zc_ne hab) (zc_ne hac) (zc_ne hpq) (zc_ne hpr) one_pos (by rw [e1', e2]; push_cast; ring)
  exact this

theorem zc_rf (p q : P) : zc (rf p) (rf q) = (starRingEnd ℂ) (zc p q) := by
  apply Complex.ext
  · simp [zc, rf]
  · simp [zc, rf]; ring

theorem zc_conj_mul (p q : P) : zc p q * (starRingEnd ℂ) (zc p q) = ((d2 p q : ℝ) : ℂ) := by
  rw [Complex.mul_conj, normSq_zc]

/-- two mirror similar triangles have opposite angles at a, modulo 2π -/
theorem sim2_lift {a b c p q r : P} (s : Sim a b c (rf p) (rf q) (rf r)) (hab : a ≠ b) (hac : a ≠ c) (hpq : p ≠ q) (hpr : p ≠ r) :
    Mod2 (Th a b - Th a c + Th p q - Th p r) := by
  obtain ⟨w, e1', e2⟩ := sim_w s
  rw [zc_rf] at e1' e2
  have d1 := d2_pos hpq
  have d3 := d2_pos hpr
  have dc : ((d2 p q : ℝ) : ℂ) ≠ 0 := by exact_mod_cast d1.ne'
  have := arg4 (k := d2 p r / d2 p q) (zc_ne hab) (zc_ne hac) (zc_ne hpr) (zc_ne hpq) (div_pos d3 d1) (by
    rw [e1', e2]
    push_cast
    field_simp
    linear_combination w * ((d2 p r : ℝ) : ℂ) * (zc_conj_mul p q) - w * ((d2 p q : ℝ) : ℂ) * (zc_conj_mul p r))
  exact Mod2.congr (by unfold Th; ring) this

/-- the base of an isosceles triangle -/
theorem isos_lift {o a b : P} (h : Cong o a o b) (hab : a ≠ b) (hoa : o ≠ a) (hob : o ≠ b) : Mod2 (2 * Th a b - Th o a - Th b o) := by
  have d1 := d2_pos hab
  have d3 := d2_pos hoa
  have dc : ((d2 a b : ℝ) : ℂ) ≠ 0 := by exact_mod_cast d1.ne'
  have hb' : b ≠ o := hob.symm
  have zab : zc a b = zc o b - zc o a := by apply Complex.ext <;> simp [zc]
  have zbo : zc b o = - zc o b := zc_swap o b
  have hA := zc_conj_mul o a
  have hB := zc_conj_mul o b
  have hC := zc_conj_mul a b
  have hh : ((d2 o a : ℝ) : ℂ) = ((d2 o b : ℝ) : ℂ) := by exact_mod_cast h
  have := arg4 (k := d2 o a / d2 a b) (zc_ne hab) (zc_ne hoa) (zc_ne hb') (zc_ne hab) (div_pos d3 d1) (by
    rw [zbo]
    push_cast
    field_simp
    rw [← hC, zab, map_sub]
    rw [hh] at hA
    rw [hh]
    linear_combination (zc o b - zc o a) * zc o a * hB - (zc o b - zc o a) * zc o b * hA)
  exact Mod2.congr (by unfold Th; ring) this

theorem midp_lift {m a b : P} (h : Midp m a b) : Mod2 (Th m a - Th b m) := by
  have e : zc m a = zc b m := by
    obtain ⟨h1, h2⟩ := h
    apply Complex.ext
    · simp [zc]; linarith
    · simp [zc]; linarith
  unfold Th
  rw [e]
  exact ⟨0, by simp⟩

theorem midp_end {m a b : P} (h : Midp m a b) : Mod2 (Th a m - Th a b) := by
  have e : ((2 : ℝ) : ℂ) * zc a m = zc a b := by
    obtain ⟨h1, h2⟩ := h
    apply Complex.ext
    · simp [zc]; linarith
    · simp [zc]; linarith
  exact arg2 two_pos e

theorem midline_lift {m n a b c : P} (h : Midp m a b) (g : Midp n a c) : Mod2 (Th m n - Th b c) := by
  have e : ((2 : ℝ) : ℂ) * zc m n = zc b c := by
    obtain ⟨h1, h2⟩ := h
    obtain ⟨g1, g2⟩ := g
    apply Complex.ext
    · simp [zc]; linarith
    · simp [zc]; linarith
  exact arg2 two_pos e

theorem para1_lift {m a b c e : P} (h : Midp m a b) (g : Midp m c e) : Mod2 (Th a c - Th e b) := by
  have k : zc a c = zc e b := by
    obtain ⟨h1, h2⟩ := h
    obtain ⟨g1, g2⟩ := g
    apply Complex.ext
    · simp [zc]; linarith
    · simp [zc]; linarith
  unfold Th
  rw [k]
  exact ⟨0, by simp⟩

theorem para2_lift {m a b c e : P} (h : Midp m a b) (g : Midp m c e) : Mod2 (Th a e - Th c b) := by
  have k : zc a e = zc c b := by
    obtain ⟨h1, h2⟩ := h
    obtain ⟨g1, g2⟩ := g
    apply Complex.ext
    · simp [zc]; linarith
    · simp [zc]; linarith
  unfold Th
  rw [k]
  exact ⟨0, by simp⟩

theorem e1_half : e1 (Real.pi / 2) = I := by
  unfold e1
  rw [Complex.exp_mul_I, ← Complex.ofReal_cos, ← Complex.ofReal_sin, Real.cos_pi_div_two, Real.sin_pi_div_two]
  simp

/-- a radius: the direction of the vector, with the variable of its point on the circle -/
theorem radius_lift {o x : P} {r : ℝ} (hr : 0 < r) (hx : On o r x) (hox : o ≠ x) : Mod2 (Th o x - 2 * tz o r x + Real.pi / 2) := by
  have z := zc_ne hox
  have et : e1 (2 * tz o r x) = uz o r x := by
    rw [← ee_tz hr hx]
    rfl
  have ab : ((Complex.abs (zc o x) : ℝ) : ℂ) = ((Real.sqrt r : ℝ) : ℂ) := by
    congr 1
    rw [Complex.abs_apply, normSq_zc]
    unfold On at hx
    rw [hx]
  rw [mod2_iff, e1_add, e1_sub, et, e1_half]
  unfold Th uz
  rw [e1_arg z, ab]
  have c := sqrt_ne_c hr
  field_simp
  ring

theorem cr_e1 {a b c : P} (hab : a ≠ b) (hac : a ≠ c) :
    cr a b a c = Complex.abs (zc a b) * Complex.abs (zc a c) * (e1 (Th a c - Th a b)).im := by
  have z1 := zc_ne hab
  have z2 := zc_ne hac
  have n1 : 0 < Complex.abs (zc a b) := by simpa using z1
  have n2 : 0 < Complex.abs (zc a c) := by simpa using z2
  have c1 := abs_c_ne z1
  have c2 := abs_c_ne z2
  have k : ((Complex.abs (zc a b) * Complex.abs (zc a c) : ℝ) : ℂ) * e1 (Th a c - Th a b) = (starRingEnd ℂ) (zc a b) * zc a c := by
    rw [e1_sub]
    unfold Th
    rw [e1_arg z1, e1_arg z2]
    have m : (starRingEnd ℂ) (zc a b) * zc a b = ((Complex.abs (zc a b) : ℝ) : ℂ) * ((Complex.abs (zc a b) : ℝ) : ℂ) := by
      rw [mul_comm, Complex.mul_conj, Complex.normSq_eq_abs]
      push_cast
      ring
    push_cast
    field_simp
    linear_combination (-((Complex.abs (zc a c) : ℝ) : ℂ) * zc a c) * m
  have i := congrArg Complex.im k
  rw [Complex.im_ofReal_mul] at i
  rw [i]
  simp [cr, zc, Complex.mul_im]
  ring

/-- a reading is a relation of directions modulo 2π -/
theorem read_lift {a b c p q r : P} (T : Mod2 (Th a b - Th a c - Th p q + Th p r)) (hab : a ≠ b) (hac : a ≠ c) (hpq : p ≠ q) (hpr : p ≠ r)
    (n : NC a b c) : Read a b c p q r := by
  have e : e1 (Th a c - Th a b) = e1 (Th p r - Th p q) := by
    rw [mod2_iff] at T
    have g : Th p r - Th p q = (Th a c - Th a b) + (Th a b - Th a c - Th p q + Th p r) := by ring
    rw [g, e1_add, T, mul_one]
  unfold NC at n
  unfold Read
  rw [cr_e1 hab hac] at n ⊢
  rw [cr_e1 hpq hpr, ← e]
  have i : (e1 (Th a c - Th a b)).im ≠ 0 := fun h => n (by rw [h, mul_zero])
  have n1 : 0 < Complex.abs (zc a b) := by simpa using zc_ne hab
  have n2 : 0 < Complex.abs (zc a c) := by simpa using zc_ne hac
  have n3 : 0 < Complex.abs (zc p q) := by simpa using zc_ne hpq
  have n4 : 0 < Complex.abs (zc p r) := by simpa using zc_ne hpr
  have s : 0 < (e1 (Th a c - Th a b)).im ^ 2 := by positivity
  have : 0 < Complex.abs (zc a b) * Complex.abs (zc a c) * (Complex.abs (zc p q) * Complex.abs (zc p r)) * (e1 (Th a c - Th a b)).im ^ 2 := by positivity
  nlinarith [this]

theorem e1_conj (t : ℝ) : (e1 (-t)).im = - (e1 t).im := by
  simp [e1, Complex.exp_im, Complex.exp_re]

theorem read2_lift {a b c p q r : P} (T : Mod2 (Th a b - Th a c + Th p q - Th p r)) (hab : a ≠ b) (hac : a ≠ c) (hpq : p ≠ q) (hpr : p ≠ r)
    (n : NC a b c) : Read2 a b c p q r := by
  have e : e1 (Th a c - Th a b) = e1 (-(Th p r - Th p q)) := by
    rw [mod2_iff] at T
    have g : -(Th p r - Th p q) = (Th a c - Th a b) + (Th a b - Th a c + Th p q - Th p r) := by ring
    rw [g, e1_add, T, mul_one]
  have e' : (e1 (Th p r - Th p q)).im = - (e1 (Th a c - Th a b)).im := by
    rw [e, e1_conj]
    ring
  unfold NC at n
  unfold Read2
  rw [cr_e1 hab hac] at n ⊢
  rw [cr_e1 hpq hpr, e']
  have i : (e1 (Th a c - Th a b)).im ≠ 0 := fun h => n (by rw [h, mul_zero])
  have n1 : 0 < Complex.abs (zc a b) := by simpa using zc_ne hab
  have n2 : 0 < Complex.abs (zc a c) := by simpa using zc_ne hac
  have n3 : 0 < Complex.abs (zc p q) := by simpa using zc_ne hpq
  have n4 : 0 < Complex.abs (zc p r) := by simpa using zc_ne hpr
  have : 0 < Complex.abs (zc a b) * Complex.abs (zc a c) * (Complex.abs (zc p q) * Complex.abs (zc p r)) * (e1 (Th a c - Th a b)).im ^ 2 := by positivity
  nlinarith [this]

end GeoCert
