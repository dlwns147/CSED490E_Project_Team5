import GeoCircle

/-!
# What the exported theorems use beyond the rules

`side/geo_lean.py` writes one theorem per certificate on top of this file.
-/

noncomputable section

namespace GeoCert

theorem eqa_flip {a b c d e f g h : P} (k : EqA a b c d e f g h) : EqA c d a b g h e f := by
  unfold EqA at *
  linear_combination (norm := pn) (-1 : ℝ) * k

theorem ratio_swap {a b c d e f g h : P} (k : Ratio a b c d e f g h) : Ratio b a d c f e h g := by
  unfold Ratio at *
  rw [d2_comm b a, d2_comm h g, d2_comm d c, d2_comm f e]
  exact k

theorem ratio_flip {a b c d e f g h : P} (k : Ratio a b c d e f g h) : Ratio e f g h a b c d := by
  unfold Ratio at *
  linear_combination (-1 : ℝ) * k

theorem coll_sw {m a b : P} (h : Coll m b a) : Coll m a b := by
  unfold Coll Para at *
  linear_combination (norm := pn) (-1 : ℝ) * h

end GeoCert
