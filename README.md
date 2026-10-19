# redteam-eval

Evaluation set for [redteam-action](https://github.com/starshiptr/redteam-action).

`main` is a small Streamlit + SQLite dashboard ([personal-dashboard](https://github.com/starshiptr/personal-dashboard)) after a security and correctness pass. Each open pull request reintroduces one real bug that the pass fixed. The Action reviews every PR. The catch rate is the number of PRs where it confirms the planted bug, out of 8. False confirms are counted separately.

Results go in the redteam-action README once the run is reviewed.
