# TwitchViewer
**TwitchViewer** is a Python script designed to run on a Raspberry Pi 5 with Ubuntu 24 LTS as the Operating System and Firefox as the browser. It provides seamless viewing and automatic switching between a predefined list of Twitch streamers, offering a fully hands-off, stand-alone solution for effortless streamer rotation.

---

## `Twitch Streamer Rotation Manager`

This project is a Python-based automation tool that integrates with the **Twitch API** and manages stream viewing sessions in **Firefox**.  
It retrieves a list of Twitch streamers from CSV files, checks who is live, and automatically opens, closes, or switches Firefox tabs to keep a rotation of streamers active.  

### `Features`
- **Twitch API Integration**  
  - Requests access tokens  
  - Validates streamers from a CSV list  
  - Fetches live stream data with retries and backoff  

- **Streamer Rotation System**  
  - Reads and updates `ROTATE_STREAMER_FILE` and `STREAMER_ROTATE_FILE`  
  - Tracks how many times each streamer has been viewed  
  - Ensures fair rotation while prioritizing streamers based on assigned priority values  

- **Firefox Window Control** (via `xdotool`)  
  - Open new Twitch stream windows  
  - Switch the active tab to a new streamer  
  - Close Twitch tabs when no streams are available  
  - Minimize all windows when idle  

- **Safe Zone Mouse Detection**  
  - Monitors mouse position  
  - Temporarily pauses Twitch processing when the cursor is near a "safe zone" edge of the screen  

- **CSV File Handling**  
  - Reads configured streamer lists (`STREAMER_ROTATE_FILE`)  
  - Writes active streamers to `ACTIVE_STREAMER_FILE`  
  - Saves rotation state to `ROTATE_STREAMER_FILE`  
  - Logs missing or invalid streamer accounts to `MISSING_STREAMER_FILE`  

### `Main Workflow`
1. **Safe Zone Check** – Pauses Twitch processing if mouse is inside the "safe zone".  
2. **Firefox State Detection** – Finds open Firefox windows and determines if a Twitch stream is already active.  
3. **Twitch API Queries** – Fetches and validates live stream data for all configured streamers.  
4. **Decision Engine** – Determines whether to open, close, switch, or do nothing with Firefox based on live stream availability and current rotation.  
5. **Rotation Tracking** – Updates counts and priorities for streamers, ensuring fairness and preventing overexposure.  

### `Key Files`
- **`STREAMER_ROTATE_FILE`** → Source list of streamers and their priorities  
- **`ACTIVE_STREAMER_FILE`** → Stores currently live streamers and their categories/games  
- **`ROTATE_STREAMER_FILE`** → Maintains rotation state and view counts  
- **`MISSING_STREAMER_FILE`** → Logs streamers not found on Twitch  

### `Requirements`
- Python 3.x  
- `requests` library  
- `xdotool` (Linux) for window and mouse control  
- Firefox browser  

### `Usage`
- Run the script directly
- Run the script via 'crontab -e'

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
It defines which streamers will be considered for viewing, their priority level, and any optional category filters that control when each streamer is eligible, seporated by commas.

**Format:**
| Priority | Streamer | Category (optional) | |
| -------- | -------- | ------------------- | --- |
| 1 | StreamerA | Music | Single category, no quotes needed |
| 2 | StreamerB | "Music,DJs" | Multiple categories, quotes required |
| 2 | StreamerC | | Empty category, no quotes needed |
| 4 | StreamerD | "-IRL,-Just Chatting,-DJs" | Multiple categories, quotes required |

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

## `ViewedStreamers.csv`
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
