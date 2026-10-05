// All manual text lives here so it can be edited without touching any component.
export const TAB_HELP = {
  kpis: {
    what: 'The headline numbers for your latest week: revenue, profit, advertising efficiency, customer acquisition and cash.',
    read: 'Each card shows the value and how it changed versus the prior period. A green triangle up is an improvement and a red triangle down is a decline (for CAC and DSO, lower is better, so a fall is shown in green). An orange card means one of your limits has been crossed.',
    act: 'Start here every week. If a card is orange, open Profit & Spend Charts or What\'s Happening to find out why.',
  },
  charts: {
    what: 'Seven charts that answer: Is the business growing profitably? Where does marketing money go? Is customer acquisition paying back? Is cash safe? Do promo weeks make money? Which months are strongest? Which channel\'s spend moves results most?',
    read: 'Dashed red lines are limits. On the cash chart and the LTV to CAC chart, the ratio or days line uses the right-hand axis. The channel chart compares spend with results over time; it shows association, not proof of cause.',
    act: 'Use Week Types to show only one type of week on the time charts. For deeper slicing, use the Interactive Explorer.',
  },
  anomalies: {
    what: 'Weeks whose combination of numbers looked unusual compared with the rest of your history.',
    read: 'The reason column explains which numbers stood out. An unusual week can be good (a record week) or bad (a loss). Click a column title to sort.',
    act: 'Check whether each flagged week had a real cause (a sale, stock-out, billing delay) or a data problem.',
  },
  segments: {
    what: 'Your weeks grouped automatically into a few types based on how they performed (margin, ROAS, CAC, discounting and so on).',
    read: 'Each card summarises one type of week: how many weeks, average margin, ROAS, CAC and profit. Comparing cards shows what separates your best weeks from your worst.',
    act: 'Click a card to filter the time charts to that type. Click it again to clear the filter.',
  },
  insights: {
    what: 'Plain-language findings from the analysis, each with the evidence behind it and a suggested action.',
    read: 'The coloured label shows importance: HIGH needs attention first, then MEDIUM, then LOW. Use the category buttons to narrow the list.',
    act: 'Work through HIGH items first. The yellow box on each card is the suggested next step.',
  },
  recommendations: {
    what: 'Specific actions ranked by priority, each with its evidence and the rule that triggered it, plus a channel-priority table.',
    read: 'The channel table compares each channel\'s recent share of spend with its peers and shows whether extra spend is still giving a good extra return (saturation).',
    act: 'Press Mark done when an action is finished. Completed actions are saved in this browser only and can be undone.',
  },
  simulations: {
    what: 'Pre-calculated what-if estimates: how profit may change if you change promo discount depth, total marketing spend, or move budget between channels.',
    read: 'Moving a slider compares that choice with your current position. A yellow warning means the choice is outside what your history has seen, so the estimate is rougher. These are estimates, not promises.',
    act: 'Use them to compare options before committing budget, then confirm with a small real-world test.',
  },
  goals: {
    what: 'Your weekly profit and revenue targets.',
    read: 'The bar shows the latest week against the target: On track at 100% or more, At risk from 80%, Behind below 80%.',
    act: 'Type your targets in the boxes. They are saved in this browser only, so set them again on a different computer.',
  },
  forecast: {
    what: 'A 13-week outlook for Net Revenue and Net Profit, built from your history.',
    read: 'The solid line is what happened, the dashed line is the forecast, and the shaded band is the 80% range: results are expected to land inside it roughly 8 times out of 10. The table lists every forecast week with its range.',
    act: 'Plan around the range, not just the middle line. Use the toggle to switch between revenue and profit, and Run forecast to read a single week.',
  },
  goal_progress: {
    what: 'How the latest week and the 4-week average compare with your targets and limits for profit, revenue, cash runway and LTV to CAC.',
    read: 'Each card shows the latest value, the target, a progress bar and a status label.',
    act: 'Anything red or orange deserves attention this week. Targets for profit and revenue come from My Targets.',
  },
  alerts: {
    what: 'Warnings raised when a monitored limit is crossed, such as a sharp revenue drop or low cash.',
    read: 'No active alerts means every monitored rule is currently satisfied. The history table lists previous pipeline runs.',
    act: 'Open an active alert, read its message, then check the related page. Your own alert thresholds are saved in this browser.',
  },
  explorer: {
    what: 'An interactive workspace for slicing your weekly data any way you like, similar to a BI tool.',
    read: 'Every number and chart on this page responds to the filters at the top. The small line under each number shows the change versus the previous equal-length period.',
    act: 'Click bars to drill down or filter, change the measure, and download the filtered weeks as a spreadsheet. See the User Manual for a walkthrough.',
  },
};

export const QUICK_START = [
  'Open This Week\'s Numbers. Look for orange cards: they are your limits being crossed.',
  'Open What\'s Happening and read the HIGH items first.',
  'Open This Quarter\'s Actions and pick the actions to do. Press Mark done as you finish them.',
  'Open 13-Week Outlook to see what the coming weeks may look like, including the range.',
  'Use the Interactive Explorer whenever you want to dig into a period, a week type or a channel.',
];

export const EXPLORER_STEPS = [
  'Slicers (top): choose a date range, years, quarters, months, week types, only unusual weeks, or only loss-making weeks. Filters combine, and "Showing X of Y weeks" tells you how many weeks match.',
  'Number cards: totals and ratios for the weeks you selected, with the change versus the previous period of the same length. The comparison is hidden when it cannot be made fairly (for example when a year or month slicer is on).',
  'Main chart: pick a measure, and optionally a second measure as a line. Click a bar to drill down one level: Year, then Quarter, then Month, then Week. Use the Up button to go back.',
  'Week type and month charts: click a bar to filter everything to it, click again to clear. Other bars stay visible but faded, so you can still compare.',
  'Relationship chart: pick any two measures to see each week as a dot, coloured by week type. The r value shows how closely they move together. It does not prove one causes the other.',
  'Table: click a column title to sort, use Previous/Next to page, and Download CSV to take the filtered weeks into Excel.',
  'Reset all filters clears everything and returns to the full history.',
];

export const EXPLORER_EXAMPLE = 'Example: why was a quarter weak? Click that year, then that quarter in the main chart, set the measure to Net Profit, then sort the table by Net Profit (low to high) to see the worst weeks and their week types.';

export const GLOSSARY = [
  ['Net Revenue', 'Sales revenue kept after deductions such as discounts and returns, as defined in your data pipeline.'],
  ['Net Profit', 'What is left of Net Revenue after the costs counted by the pipeline, including product and marketing costs.'],
  ['Net Margin %', 'Net Profit divided by Net Revenue, times 100. In the Explorer it is calculated from totals, not by averaging weekly percentages.'],
  ['Gross Margin %', 'Share of revenue left after the direct cost of the products sold.'],
  ['ROAS (return on ad spend)', 'Revenue generated per 1 of advertising spend. Below the break-even level shown on the Numbers page, advertising is not paying for itself.'],
  ['CAC (customer acquisition cost)', 'Average marketing cost of winning one new customer. Lower is better.'],
  ['LTV (lifetime value)', 'The value a customer is expected to bring over the whole relationship.'],
  ['LTV to CAC', 'Lifetime value divided by acquisition cost. Higher is better; your minimum is shown under Your current limits below.'],
  ['DSO (days sales outstanding)', 'Average number of days it takes to collect payment after a sale. Lower is better.'],
  ['Receivables (AR outstanding)', 'Money customers owe you but have not yet paid.'],
  ['Cash runway (weeks)', 'How many weeks your cash would last at the current rate of spending. Your minimum is shown under Your current limits.'],
  ['Discount rate %', 'The share of revenue given away in discounts.'],
  ['Return rate %', 'The share of orders or revenue that comes back as returns.'],
  ['Conversion rate %', 'The share of visits that become orders.'],
  ['Marketing % of revenue', 'Marketing spend as a share of Net Revenue.'],
  ['Loss-making week', 'A week in which Net Profit was below zero.'],
  ['Week type (segment)', 'A group of weeks that performed similarly. The grouping is found automatically from the numbers.'],
  ['Unusual week (anomaly)', 'A week whose combination of numbers differs from your normal pattern. It is a prompt to look closer, not automatically a problem.'],
  ['80% range', 'The band around a forecast in which the result is expected to fall about 8 times out of 10.'],
  ['Saturation', 'When extra spend on a channel brings smaller and smaller extra results.'],
  ['Marginal return', 'The extra result gained from one more unit of spend on a channel.'],
  ['Lag (for example "Search, lag 2w")', 'Looks at whether this week\'s spend lines up with results a number of weeks later.'],
  ['Pre-computed what-if', 'An estimate prepared in advance from your history, shown instantly when you move a slider.'],
  ['r (correlation)', 'A number from -1 to +1 showing how closely two measures move together. Near 0 means no clear link. It never proves cause and effect.'],
];

export const FAQ = [
  ['A page says "Run main.py to generate your data".', 'The analysis files for that page are missing or could not be read. Ask your administrator to run the analysis pipeline and refresh the data, then reload this page.'],
  ['The numbers look old.', 'The dashboard shows the results of the most recent pipeline run. It does not update on its own between runs. "Last updated" at the top shows when the data was refreshed, when available.'],
  ['Why does the forecast show a range?', 'Nobody can predict the future exactly. The shaded 80% range shows how much results may reasonably vary. Plan for the range.'],
  ['Why does a what-if show a warning?', 'The choice is outside what your history has seen. The estimate is then less reliable.'],
  ['My targets or "Mark done" ticks disappeared.', 'They are stored in the web browser you used. A different browser, a different computer, or cleared browser data starts fresh.'],
  ['Why do some Explorer comparisons say "-"?', 'A fair comparison needs a full previous period of the same length. When a year, quarter or month slicer is on, or when you view the whole history, there is nothing fair to compare against.'],
  ['How are CAC, LTV to CAC and DSO combined over several weeks?', 'As a simple average of the weekly values. Cash and receivables show the latest week in view. Revenue, profit and spend are summed.'],
  ['Can I trust the channel and what-if numbers as exact?', 'Treat them as informed estimates. They are based on past patterns, and patterns can change.'],
];

export const ACCURACY_NOTES = [
  'Forecasts, what-if results and channel comparisons are estimates built from historical patterns. They guide decisions; they do not guarantee outcomes.',
  'Two measures moving together (correlation) does not prove one causes the other.',
  'Explorer totals are sums of weekly values. Ratios such as Net Margin % are computed from those totals.',
  'Definitions follow your analysis pipeline. If you are unsure of an exact definition, ask the person who set up the analysis.',
];
