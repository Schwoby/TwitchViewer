# TwitchViewer
**TwitchViewer** is a Python script designed to run on a Raspberry Pi 5 with Ubuntu 24 LTS as the Operating System. It provides seamless viewing and automatic switching between a predefined list of Twitch streamers, offering a fully hands-off, stand-alone solution for effortless streamer rotation.

---

## `TwitchViewer.py`
This is the main script. Use caution when editing it.
### 1. Mouse Position Check
- If the mouse is inside the skip zone:  
  1. The script pauses before rechecking.  
  2. If the mouse remains in the skip zone, the script exits.  
- If the mouse is outside the skip zone, the script continues.
### 2. Check for Active Twitch Streamers
- Load `TwitchStreamers.csv` and detect which streamers are live.
- Determine which streamers qualify for viewing.
- Save results to `LiveStreamers.csv`.
### 3. Compare Streamer Results
- Compare active streamers against `ViewingStreamers.csv`.
  - Remove any streamers no longer active.
  - Add any newly active streamers not already listed.
### 4. Browser Check
- If a browser is open, check if it’s displaying a Twitch streamer and mark that streamer as the **Current Streamer**.
### 5. Compare Browser Result to `ViewingStreamers.csv`
- If the browser is open **and** the **Current Streamer** has not reached their view limit, keep them as the **Selected Streamer**.
- If the **Current Streamer** has reached their view limit, select the next eligible streamer instead.
- If no browser is open, or the browser is not on a Twitch page, clear the **Current Streamer** and pick the next eligible streamer.
- If no eligible streamers are found, set the **Selected Streamer** to `null`.
### 6. Activate Streamer / Browser
- Increment the `Count` field in `ViewingStreamers.csv` for the **Selected Streamer**.
- If the **Current Streamer** differs from the **Selected Streamer**, navigate to the **Selected Streamer**.
- If there is no **Current Streamer**, open a new tab to the **Selected Streamer**.
- If the **Current Streamer** is set but the **Selected Streamer** is `null`, close the tab.

---

## `Settings.py`
Holds settings that control viewer behavior. Some examples:
- How many loops before switching streamers (when available)
- File names and paths
- Skip zone coordinates
- Skip zone delay

---

## `Account.py`
Contains the Twitch authorization details.

---

## `TwitchStreamers.csv`
**This file must be filled out before running the script.**  
It defines which streamers will be considered for viewing, their priority level, and any optional category filters that control when each streamer is eligible.

**Format:**
| Priority | Streamer | Category (optional) |
| -------- | -------- | ------------------- |
| 1 | StreamerA | Music, DJs, Art |
| 2 | StreamerB | -IRL, -Just Chatting |
| 2 | StreamerC | |
| 4 | StreamerD | |

**Details:**
- `Priority` is an integer for controlling order.
- Multiple streamers can share the same priority.
- `Priority` **1** is the highest and takes precedence.
  - If multiple Priority 1 streamers are live, the top-most is chosen first.
  - Priority 1 streamers do not rotate.
- `Priority` **2** and higher participate in rotation:
  - The rotation starts with the lowest priority found and includes streamers up to double that value.
    - Example: If a Priority 3 streamer is found, streamers with Priority 3–5 are included; Priority 6+ is excluded.
- `Streamer` is not case-sensitive.
- If a `Streamer` appears more than once, only the final row will be considered.
- `Category` is optional and matches Twitch’s game categories:
  - If specified, the streamer is only considered if they are streaming in that category.
  - If prefixed with `-`, the streamer is skipped if they are streaming in that category.
  - If blank, any category is accepted.

---

## `LiveStreamers.csv`
**This file is not actively used by the script.**
Log of all live streamers found during checks.  

**Format:**
| Priority | Streamer | Category |
| -------- | -------- | -------- |
| 2 | StreamerB | Music |
| 2 | StreamerC | IRL |

---

## `ViewingStreamers.csv`
**This file is actively used by the script.**
Tracks which streamers have been selected for viewing and how many times each has been shown.  

**Format:**
| Count | Streamer |
| ----- | -------- |
| 3 | StreamerB |
| 0 | StreamerC |

---

## `Disclaimer`
1. This is a personal project provided **"as-is"** with no warranty or guarantee of any kind. Use it at your own risk.
2. This project is not affiliated with, endorsed by, or sponsored by Twitch Interactive, Inc. Twitch and all related trademarks are the property of their respective owners. Use of Twitch services is subject to Twitch's terms of service and licensing agreements. Users are responsible for complying with Twitch's policies when using this software.
