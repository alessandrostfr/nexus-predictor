# Model notes

The MVP uses interpretable scoring rather than a complex black-box model. This is deliberate: the historical public dataset is useful, but still small and partly estimated.

## Attendance prediction

Attendance prediction combines historical baseline, lineup size, event duration, stage count, top artist demand and returning artist ratio. The result is a low/mid/high range, not an official attendance figure.

## Artist demand score

Artist demand scoring uses explainable factors: lineup presence, previous appearances, returning artist bonus, recent presence, subgenre context, manual hype, performance format and special show handling.

## Genre classification

Genre classification is deterministic: manual override, curated seed, keyword/rule match and Unknown fallback.

## Room pressure score

Room pressure combines estimated room capacity, artist demand, time-band curve, candidate artists and timetable source status. Until official slots are imported, values remain theoretical and are clearly labelled in the UI.

## Future improvements

Future work can improve the model through official timetable import, ticketing signals, confirmed attendance, better public API popularity signals and post-event calibration.
