# Testing the prototype with assistive technology

A script for the people who will try the prototype with a screen reader, with the keyboard alone, with a switch, with voice control, or with a screen magnifier. [`ACCESSIBILITY.md`](ACCESSIBILITY.md) lists what programs have checked; this page is for what only a person can check: whether the page *makes sense* when it is used this way, not only whether its names and roles are present.

**Nothing in this script has been run.** No screen reader, switch device, voice control program or magnifier has been used with the page by anyone, and nobody with a disability has tested it. When it is run, the results go in the table at the end and into `ACCESSIBILITY.md`, which today says "not checked" in these places.

## Who should do this

- **People who use the technology every day, and are paid for the time.** Someone who uses a screen reader all day finds in ten minutes what a developer who turned one on for the first time never finds, and knows the difference between "unusual" and "broken".
- A developer or tester using a screen reader for an hour is a smoke test. It finds missing names and dead ends, and it is worth doing, but it must not be reported as "tested with a screen reader".
- Two people for each kind of technology, if you can: one person's habits are not everyone's.
- Do not ask someone to test while the page is in a state you have to explain. Give them the tasks below and stay quiet.

## What to set up

The page is one file and a folder of fonts. It makes **no request to any other site**, so it works on a computer with no network (`prototype/b22.py` shows this by refusing every outside request and still reaching the Home screen). Every number in it is made up.

```bash
python3 -m http.server --directory prototype/project 8000
# then open  http://127.0.0.1:8000/Main.dc.html
```

Use the prototype as it is; do not give testers real requirements.

| Technology | Combinations to try first | Notes |
|---|---|---|
| Screen reader | NVDA with Firefox and with Chrome (Windows); VoiceOver with Safari (macOS and iPhone); TalkBack with Chrome (Android); Orca with Firefox (Linux) | The page has only been run in Chromium by the people who made it. A problem that shows in one browser and not the other is a finding, not an argument |
| Keyboard alone | Any desktop browser | No mouse, no touchpad. Tab, Shift+Tab, Enter, Space, arrow keys, Escape |
| Switch access or sequential scanning | Whatever the tester already uses | Ask what they use; do not give them a tool they do not know |
| Voice control | Dragon, Voice Control (macOS, iOS), Windows Voice Access | Controls are named by what is written on them; ask the tester which names they had to guess |
| Magnification and reflow | 200 percent text-only zoom, 400 percent page zoom, a screen magnifier, a phone | Also high-contrast or forced-colours mode, and a dark system theme |

## The tasks

Give each task as one sentence, with no hints about where things are. For each, note whether it was done, how long it took, where they stopped, what they said, and anything the technology announced that was wrong, missing or confusing.

| # | Task | The risk this one is there to test |
|---|---|---|
| 1 | Open the sample project and get to the Home screen | The opening screen, the mapping step, the announcement that the page changed ("Now showing: ...") |
| 2 | Say how many clusters are waiting for you, and which one needs the most attention | Headings, landmarks, the order of the page, whether numbers are read with their labels |
| 3 | Open a cluster and say how its wordings differ from each other | The wording comparison (changed words are marked in colour; are they marked in words too?), the table of wordings, the window that lines the words up in columns (does focus go in, stay in, and come back; does Escape close it) |
| 4 | Decide it with a reason and see what changed | Form labels, the reason code menu, errors and confirmations announced without moving focus, the status line |
| 5 | Find where the status of every requirement is shown, and say which are waiting | **All requirements.** The map is a picture of coloured squares and is hidden from a screen reader on purpose; the list under it is the way in. Is the list enough? Does the person know the picture exists? |
| 6 | Find the engineering V and say what it tells you about verification | Pictures with meaning (hidden or named?), the counts on each level, anything that is only visible |
| 7 | Label ten pairs on Label pairs, then undo the last one | Keyboard shortcuts (keys 1 to 6) alongside a screen reader's own keys; does the page announce the next pair; the blind rule means a screen reader must not read out anything about the app's answer |
| 8 | Save your work to a file, close the tab, open it again, and load the file | The file picker, the messages after loading, what is announced when a file is refused |
| 9 | Find out whether the AI is switched on, and what it would be allowed to see | The data sheet, the switch, the "held back" groups. A switch's state must be said, not shown |
| 10 | Ask a colleague for a second opinion on a cluster, then find it waiting | Hand-offs: the list of people, the waiting state |

For the phone, do tasks 1, 2, 4 and 8 at 390 px wide, in the orientation the tester prefers.

## Things the programs cannot judge, to ask about every time

- **Reading order.** Is it the order a person would want, or the order the page happens to be built in?
- **Verbosity.** Is anything read out that adds nothing (a decorative icon, the same name twice), or is something important never read at all?
- **Meaning that depends on layout.** "The column on the right", "the red one": does anything on the page say it that way?
- **Surprises.** Does focus ever jump, vanish or land somewhere unexpected after an action? Does a change happen that nobody is told about?
- **Effort.** How many key presses to do task 4? Is it more than a mouse user needs by a lot?
- **Names.** Which name would the person say aloud to reach a control, and is that the name on it?
- **Time.** Is there anything that times out or moves by itself?

## How to report what you find

One finding per line in the table below. Say what the person did, what happened, what they expected, and how much it mattered to them. Quote the page's wording if it helps; it is made-up text. Keep the technology and its version, and the browser and its version: a result with neither cannot be repeated.

| Severity | Meaning |
|---|---|
| Blocks | The task cannot be done this way |
| Hard | It can be done, with effort or a workaround the person had to find |
| Rough | It can be done, but it was unclear or irritating |
| Idea | The person suggests something better |

Do not average, and do not drop a finding because only one person had it.

## What to do with the findings

1. A "blocks" or "hard" finding gets a check added to `prototype/b20.py` (or a note saying why a program cannot check it), then the fix, in that order, so it cannot come back.
2. Update the "What has not been checked" list in [`ACCESSIBILITY.md`](ACCESSIBILITY.md): say which technologies were used, by how many people, on which date, and what was found. Do not write "accessible"; write what was tried.
3. If it is the first time, say so in the project's [`README.md`](../README.md) table, in place of "no screen reader ... has been used".

## Results

| Date | Technology and version | Browser and version | Tester (role, not name) | Task | Result | Severity | What happened |
|---|---|---|---|---|---|---|---|
| | | | | | | | *(empty: nothing has been run)* |

## What has and has not been checked

| Checked | How |
|---|---|
| The page opens with no network and reaches its screens | `prototype/b22.py` |
| The names, roles, headings, landmarks, contrast, keyboard order, reflow and chart colours | `prototype/b20.py`, in Chromium, as listed in [`ACCESSIBILITY.md`](ACCESSIBILITY.md) |
| **Not checked** | **Everything in this script.** The tasks and the questions are the authors' guesses about where problems will be; a tester will find others. The Firefox and WebKit jobs in CI run some of the browser tests, but they have never run, so even automated results for those browsers do not exist yet |
