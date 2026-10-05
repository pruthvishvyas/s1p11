import os, sys, time, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.config import CONFIG
from src.data.ingest        import run_ingest
from src.data.clean         import run_clean
from src.features.engineer  import run_engineer
from src.analytics.eda      import run_eda
from src.models.classifier  import run_classifier
from src.models.segmentation import run_segmentation
from src.models.predictor   import run_predictor
from src.analytics.business_logic import run_business_logic
from src.analytics.insights import run_insights
from src.reporting.export   import run_export

PHASES = [
    ('Ingest',         run_ingest,         {}),
    ('Clean',          run_clean,          {}),
    ('Engineer',       run_engineer,       {}),
    ('EDA',            run_eda,            {}),
    ('Segmentation',   run_segmentation,   {}),
    ('Classifier',     run_classifier,     {}),
    ('Predictor',      run_predictor,      {}),
    ('Business Logic', run_business_logic, {}),
    ('Insights',       run_insights,       {}),
    ('Export',         run_export,         {}),
]

pipeline_start = time.time()
context        = {}
phase_times    = {}
failed         = []

for name, fn, extra in PHASES:
    print(f'\n{"="*55}\n  PHASE: {name}\n{"="*55}')
    t0 = time.time()
    try:
        result = fn(config=CONFIG, **context, **extra)
        context.update(result)
        phase_times[name] = time.time() - t0
        print(f'  ✅ {name} completed in {phase_times[name]:.1f}s')
    except Exception as e:
        phase_times[name] = time.time() - t0
        failed.append(name)
        print(f'  ❌ {name} FAILED: {e}')
        traceback.print_exc()

total = time.time() - pipeline_start
print(f'\n{"="*55}')
print(f'  Pipeline complete in {total:.1f}s' + (f'  | FAILED: {", ".join(failed)}' if failed else '  | all phases OK'))
for k, v in phase_times.items():
    print(f'  {k:<20} {v:.1f}s')
print(f'{"="*55}')
print('Next: python report.py   |   python app.py')
sys.exit(1 if failed else 0)

