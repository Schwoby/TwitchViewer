import subprocess
import webbrowser
import requests
import time
import csv
import os
import re
from requests.exceptions import Timeout
from Account import CLIENT_ID, CLIENT_SECRET
from Settings import (
    TOKEN_URL,
    TWITCH_API_URL,
    STREAMER_ROTATE_FILE,
    ACTIVE_STREAMER_FILE,
    ROTATE_STREAMER_FILE,
    SCREEN_SAFE_ZONE,
    SAFE_ZONE_RECHECK,
    MISSING_STREAMER_FILE
)

_screen_size_cache = {"width": None, "height": None}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def force_kill_firefox():
    subprocess.run(["pkill", "firefox"])

def get_screen_width():
    if _screen_size_cache["width"] is not None:
        return _screen_size_cache["width"]
    if os.getenv("DISPLAY") is None:
        width = 1920
        _screen_size_cache["width"] = width
        return width
    try:
        output = subprocess.run(["xrandr"], capture_output=True, text=True)
        for line in output.stdout.split("\n"):
            if " connected " in line and "+" in line:
                parts = line.split()
                for part in parts:
                    if "x" in part and "+" in part:
                        width = int(part.split("x")[0])
                        _screen_size_cache["width"] = width
                        return width
    except Exception:
        pass
    width = 1920
    _screen_size_cache["width"] = width
    return width

def get_screen_height():
    if _screen_size_cache["height"] is not None:
        return _screen_size_cache["height"]
    if os.getenv("DISPLAY") is None:
        height = 1080
        _screen_size_cache["height"] = height
        return height
    try:
        output = subprocess.run(["xrandr"], capture_output=True, text=True)
        for line in output.stdout.split("\n"):
            if " connected " in line and "+" in line:
                parts = line.split()
                for part in parts:
                    if "x" in part and "+" in part:
                        height = int(part.split("x")[1].split("+")[0])
                        _screen_size_cache["height"] = height
                        return height
    except Exception:
        pass
    height = 1080
    _screen_size_cache["height"] = height
    return height

def get_mouse_position():
    try:
        output = subprocess.run(["xdotool", "getmouselocation"], capture_output=True, text=True, check=True)
        pos_data = output.stdout.strip().split()
        return int(pos_data[0].split(":")[1])
    except (subprocess.CalledProcessError, IndexError, ValueError):
        return 960

def move_mouse_to_position(x, y):
    try:
        subprocess.run(["xdotool", "mousemove", str(x), str(y)], check=True)
    except subprocess.CalledProcessError:
        print("Failed to move mouse.")

def should_skip_twitch_check_and_move_mouse():
    screen_width = get_screen_width()
    mouse_x = get_mouse_position()
    safe_zone = int(SCREEN_SAFE_ZONE)
    in_safe_zone = mouse_x >= (screen_width - safe_zone)
    screen_height = get_screen_height()
    if in_safe_zone:
        move_mouse_to_position(screen_width, int(screen_height * 0.5))
    else:
        move_mouse_to_position(int(screen_width * 0.5), int(screen_height - 120))
    return in_safe_zone

def check_firefox_streamer():
    result_data = {
        "total_windows": 0,
        "streamer": None,
    }
    try:
        # Count Firefox windows
        result = subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--class", "firefox"],
            capture_output=True, text=True, timeout=5
        )
        window_ids = result.stdout.splitlines()
        total_windows = len(window_ids)
        result_data["total_windows"] = total_windows

        if total_windows > 2:
            try:
                subprocess.run(
                    ["xdotool", "search", "--onlyvisible", "--class", "firefox", "windowclose", "%@"],
                    capture_output=True, text=True, timeout=5
                )
            except subprocess.TimeoutExpired:
                force_kill_firefox()
            except Exception:
                force_kill_firefox()
            result_data["total_windows"] = 0
            print(f"Firefox windows: {result_data['total_windows']}")
            return result_data

        streamer_found = False
        if total_windows >= 1:
            for win_id in window_ids:
                try:
                    title_result = subprocess.run(
                        ["xdotool", "getwindowname", win_id],
                        capture_output=True, text=True, timeout=5
                    )
                    title = title_result.stdout.strip()
                    if title.lower().endswith(" - twitch — mozilla firefox"):
                        streamer_name = title[:-len(" - twitch — mozilla firefox")].strip()
                        if streamer_name.startswith("("):
                            first_space_index = streamer_name.find(" ")
                            if first_space_index != -1:
                                streamer_name = streamer_name[first_space_index + 1:]
                        result_data["streamer"] = streamer_name
                        # Activate Twitch window
                        subprocess.run(["xdotool", "windowactivate", win_id])
                        streamer_found = True
                        break
                except Exception:
                    continue

            if not streamer_found:
                # Fallback: activate first Firefox window if Twitch not found
                subprocess.run(["xdotool", "windowactivate", window_ids[0]])

        print(f"Firefox windows: {result_data['total_windows']}")
        print(f"Active streamer: {result_data['streamer']}")
        print(f"")
    except Exception:
        pass
    return result_data

def get_access_token():
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    try:
        response = requests.post(TOKEN_URL, data=data, timeout=10)
        response.raise_for_status()
        return response.json()['access_token']
    except Timeout:
        print("Twitch API token request timed out (10s).")
        return None
    except requests.RequestException as e:
        print(f"Error obtaining access token: {e}")
        return None

def read_streamers(csv_file):
    streamers = []
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            streamers.append({
                'priority': (row.get('Priority') or '').strip(),
                'name': row['Streamer'].strip(),
                'category': (row.get('Category') or '').strip()
            })
    return streamers

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def requests_get_with_retries(url, headers=None, params=None, timeout=10, retries=2, backoff=1):
    """
    Wrapper for requests.get with simple retry on exceptions.
    retries: number of retries after first failure.
    backoff: seconds to wait between retries.
    Returns response or None on repeated failure.
    """
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.Timeout:
            print(f"Twitch API request timed out (attempt {attempt+1}/{retries+1}).")
        except requests.RequestException as e:
            print(f"Twitch API request error (attempt {attempt+1}/{retries+1}): {e}")
        if attempt < retries:
            time.sleep(backoff)
    return None

def get_valid_users(streamers, token):
    if not token:
        return {}, []
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {token}'
    }
    url = "https://api.twitch.tv/helix/users"
    valid_users = {}
    not_found = []
    for batch in chunks(streamers, 100):
        params = [('login', s['name'].strip().lower()) for s in batch]
        r = requests_get_with_retries(url, headers=headers, params=params, timeout=10)
        if r is None:
            return {}, []
        data = r.json().get('data', [])
        found_logins = {u['login']: u for u in data}
        for s in batch:
            login = s['name'].strip().lower()
            if login in found_logins:
                valid_users[login] = {
                    'twitch_user': found_logins[login],
                    'category': s['category'],
                    'priority': s['priority']
                }
            else:
                not_found.append(login)
    return valid_users, not_found

def get_live_streams(valid_users, token):
    if not token:
        return []
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {token}'
    }
    live_streams = []
    valid_logins = list(valid_users.keys())
    for batch in chunks(valid_logins, 100):
        params = [('user_login', login) for login in batch]
        r = requests_get_with_retries(TWITCH_API_URL, headers=headers, params=params, timeout=10)
        if r is None:
            return []
        data = r.json().get('data', [])
        for stream in data:
            login = stream['user_login'].lower()
            user_info = valid_users[login]
            game = stream.get('game_name') or "none"
            category = user_info['category'] if user_info['category'] else ''
            live_streams.append({
                'priority': user_info['priority'],
                'name': stream['user_name'],
                'game': game,
                'category': category
            })
    return live_streams

def write_live_streamers_csv(filename, live_streams):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Priority', 'Streamer', 'Category', 'Game'])
        for s in live_streams:
            cat = s['category'] or ''
            writer.writerow([s['priority'], s['name'], cat, s['game']])

def passes_category_game_filter(s):
    category = s['category']
    game = s['game']
    if not category:
        return True
    category_strip = category.strip()
    if category_strip.startswith('(') and category_strip.endswith(')'):
        category_strip = category_strip[1:-1].strip()
    categories = [c.strip() for c in category_strip.split(',')] if category_strip else []
    categories_lower = [c.lower() for c in categories]
    game_lower = game.lower()
    negation_match = any(cat.startswith('-') and cat[1:].lower() == game_lower for cat in categories_lower)
    if negation_match:
        return False
    positive_match = any(not cat.startswith('-') and cat.lower() == game_lower for cat in categories_lower)
    return positive_match

def write_rotate_streamer_file(filename, live_streams):
    # This function no longer writes, but you can adapt it if needed for writing in the future
    pass  # Placeholder

def read_rotate_streamers(filename):
    """
    Reads ROTATE_STREAMER_FILE CSV and returns list of dicts with all columns,
    but ensures 'Count' is int (default 0 if missing or invalid).
    """
    rows = []
    try:
        with open(filename, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize count
                try:
                    row['Count'] = int(row.get('Count', 0))
                except Exception:
                    row['Count'] = 0
                rows.append(row)
    except Exception:
        pass
    return rows

def compare_rotate_streamers(live_streams):
    result_data = {"lowest_priority": None, "new_streamers": set(), "removed_streamers": set(), "updated_list": [], "firefox_found": False}
    def _normalize(name):
        if name is None:
            return ""
        s = str(name).strip()
        s = re.sub(r'^\([^)]*\)\s*', '', s)
        return s.lower()
    try:
        filtered_streamers = [s for s in live_streams if passes_category_game_filter(s)]
    except Exception:
        filtered_streamers = []
    lowest_priority = None
    for s in filtered_streamers:
        try:
            prio_val = int(s.get('priority', s.get('Priority', 999999)))
            if lowest_priority is None or prio_val < lowest_priority:
                lowest_priority = prio_val
        except Exception:
            continue
    if lowest_priority is None:
        lowest_priority = 999999
    result_data["lowest_priority"] = lowest_priority
    filtered_streamers = [s for s in filtered_streamers if int(s.get('priority', s.get('Priority', 999999))) < 2 * lowest_priority]
    current_names = []
    for s in filtered_streamers:
        try:
            name = s.get('name') or s.get('streamer') or s.get('display_name') or s.get('login') or str(s)
            name = str(name).strip()
            name = re.sub(r'^\([^)]*\)\s*', '', name)
            current_names.append(name)
        except Exception:
            continue
    current_norm_set = {_normalize(n) for n in current_names}
    try:
        existing_rotate_streamers = read_rotate_streamers(ROTATE_STREAMER_FILE) or []
    except Exception:
        existing_rotate_streamers = []
    existing_list = []
    norm_to_count = {}
    for row in existing_rotate_streamers:
        streamer_name = None
        if isinstance(row, dict):
            for key in ('Streamer', 'streamer', 'name', 'display_name', 'login'):
                if key in row and row[key]:
                    streamer_name = row[key]
                    break
        if streamer_name:
            existing_list.append(streamer_name)
            norm_name = _normalize(streamer_name)
            try:
                norm_to_count[norm_name] = int(row.get('Count', 0))
            except Exception:
                norm_to_count[norm_name] = 0
        else:
            existing_list.append(str(row))
    for s in live_streams:
        try:
            name = s.get('name') or s.get('streamer') or s.get('display_name') or s.get('login') or str(s)
            norm_name = _normalize(name)
            count_val = s.get('Count', s.get('count', 0))
            count_val = int(count_val) if isinstance(count_val, (int, str)) and str(count_val).isdigit() else 0
            norm_to_count[norm_name] = max(norm_to_count.get(norm_name, 0), count_val)
        except Exception:
            continue
    existing_norm_map = {}
    for orig in existing_list:
        try:
            existing_norm_map[_normalize(orig)] = orig
        except Exception:
            existing_norm_map[_normalize(str(orig))] = str(orig)
    existing_norm_set = set(existing_norm_map.keys())
    new_norms = current_norm_set - existing_norm_set
    new_streamers = {n for n in current_names if _normalize(n) in new_norms}
    removed_norms = existing_norm_set - current_norm_set
    removed_streamers = {existing_norm_map[norm] for norm in removed_norms if norm in existing_norm_map}
    result_data["new_streamers"] = new_streamers
    result_data["removed_streamers"] = removed_streamers
    updated_list = [orig for orig in existing_list if _normalize(orig) in current_norm_set]
    for ns in new_streamers:
        if ns not in updated_list:
            updated_list.append(ns)
    try:
        base_order_data = read_rotate_streamers(STREAMER_ROTATE_FILE) or []
    except Exception:
        base_order_data = []
    base_order_list = []
    for row in base_order_data:
        if isinstance(row, dict):
            for key in ('Streamer', 'streamer', 'name', 'display_name', 'login'):
                if key in row and row[key]:
                    base_order_list.append(row[key])
                    break
        else:
            base_order_list.append(str(row))
    base_order_norm = [_normalize(x) for x in base_order_list]
    updated_list.sort(key=lambda x: base_order_norm.index(_normalize(x)) if _normalize(x) in base_order_norm else len(base_order_norm))
    result_data["updated_list"] = updated_list
    if not result_data["new_streamers"]:
        result_data["new_streamers"] = None
    if not result_data["removed_streamers"]:
        result_data["removed_streamers"] = None
    print(f"")
    print("New streamers to add:", result_data["new_streamers"])
    print("Streamers no longer in rotation:", result_data["removed_streamers"])
    count_name_sets = []
    for s in updated_list:
        norm_s = _normalize(s)
        count = norm_to_count.get(norm_s, 0)
        priority = None
        for live_s in live_streams:
            name_match = live_s.get('name') or live_s.get('streamer') or live_s.get('display_name') or live_s.get('login')
            if name_match and _normalize(name_match) == norm_s:
                priority = live_s.get('priority', live_s.get('Priority', 'N/A'))
                break
        count_name_sets.append((count, s, priority))
    firefox_action_decider(count_name_sets)
    return result_data

def firefox_action_decider(count_name_sets):
    print(f"")
    print(f"Firefox Streamer: {firefox_data['streamer']}")
    print(f"Active Streamer Count: {len(count_name_sets)}")
    print(f"")
    if firefox_data['streamer'] is None and len(count_name_sets) == 0:
        minimize_windows()
        print(f"Minimize Windows")
    elif firefox_data['streamer'] is None and len(count_name_sets) == 1:
        open_firefox_window(count_name_sets[0][1])
        count_name_sets = update_count_value(count_name_sets[0][1],count_name_sets)
        print(f"Open Browser (to {count_name_sets[0][1]})")
    elif firefox_data['streamer'] is not None and len(count_name_sets) == 0:
        close_firefox_window()
        print(f"Close Browser Tab")
    elif firefox_data['streamer'] is not None and len(count_name_sets) == 1:
        if count_name_sets[0][1] == firefox_data['streamer']:
            count_name_sets = update_count_value(firefox_data['streamer'],count_name_sets)
            print(f"Do Nothing")
        else:
            edit_firefox_window(count_name_sets[0][1])
            count_name_sets = update_count_value(count_name_sets[0][1],count_name_sets)
            print(f"Retain Browser, Change Streamer (to {count_name_sets[0][1]})")
    elif firefox_data['streamer'] is not None and len(count_name_sets) > 1:
        if any(count == 1 and name == firefox_data['streamer'] for count, name, priority in count_name_sets):
            count_name_sets = update_count_value(firefox_data['streamer'],count_name_sets)
            print(f"Do Nothing")
        elif any(count < 3 and name == firefox_data['streamer'] for count, name, priority in count_name_sets):
            count_name_sets = update_count_value(firefox_data['streamer'],count_name_sets)
            print(f"Do Nothing")
        else:
            # current streamer has count >= 3, need to pick a new streamer
            sorted_streamers = sorted(count_name_sets, key=lambda x: (-x[0], x[2]))
            streamers_under_3 = [s for s in sorted_streamers if s[0] < 3]
            if streamers_under_3:
                selected_streamer = min(streamers_under_3, key=lambda x: x[2])[1]  # pick lowest priority
                edit_firefox_window(selected_streamer)
                count_name_sets = update_count_value(selected_streamer,count_name_sets)
                print(f"Retain Browser, Change Streamer (to {selected_streamer})")
            else:
                other_streamers = [s for s in sorted_streamers if s[1] != firefox_data['streamer']]
                if other_streamers:
                    first_other_streamer = min(other_streamers, key=lambda x: x[2])[1]
                    count_name_sets = [(0, name, priority) for _, name, priority in count_name_sets]
                    edit_firefox_window(first_other_streamer)
                    count_name_sets = update_count_value(first_other_streamer,count_name_sets)
                    print(f"Retain Browser, Reset Streamer Counts, Change Streamer (to {first_other_streamer})")
    elif firefox_data['streamer'] is None and len(count_name_sets) > 1:
        sorted_streamers = sorted(count_name_sets, key=lambda x: (-x[0], x[2]))
        streamers_under_3 = [s for s in sorted_streamers if s[0] < 3]
        first_priority_1 = next((name for count, name, priority in sorted_streamers if priority == 1), None)
        if first_priority_1:
            selected_streamer = first_priority_1
        elif streamers_under_3:
            selected_streamer = min(streamers_under_3, key=lambda x: x[2])[1]  # pick lowest priority under 3
        else:
            selected_streamer = min(sorted_streamers, key=lambda x: x[2])[1]  # pick lowest priority overall
        open_firefox_window(selected_streamer)
        count_name_sets = update_count_value(selected_streamer,count_name_sets)
        print(f"Open Browser (to {selected_streamer})")
    else:
        print(f"MORE WORK TO BE DONE")
    save_rotate_streamers(count_name_sets, ROTATE_STREAMER_FILE)
    for count, name, priority in count_name_sets:
        print(f"{count} - {name} - {priority}")

def update_count_value(streamer, count_name_sets):
    updated_sets = [
        (count + 1 if name == streamer else count, name, priority)
        for count, name, priority in count_name_sets
    ]
    return updated_sets

def open_firefox_window(streamer):
    """control Firefox by opening a new window/tab."""
    webbrowser.open("https://www.twitch.tv/" + streamer)

def edit_firefox_window(streamer):
    """Control Firefox by redirecting the active tab to the given streamer."""
    try:
        # Find the first visible Firefox window
        win_id = subprocess.check_output(
            ["xdotool", "search", "--onlyvisible", "--class", "Firefox"]
        ).decode().splitlines()[0]
        # Activate the window
        subprocess.run(["xdotool", "windowactivate", win_id])
        time.sleep(0.5)  # Small delay for stability
        # Focus the address bar
        subprocess.run(["xdotool", "key", "ctrl+l"])
        time.sleep(0.5)  # Small delay for stability
        # Type Twitch URL and navigate
        subprocess.run(["xdotool", "type", "--delay", "100", f"https://www.twitch.tv/{streamer}"])
        subprocess.run(["xdotool", "key", "Return"])
    except IndexError:
        print("No Firefox window found to activate")
    except subprocess.CalledProcessError:
        print("xdotool command failed")

def close_firefox_window():
    """Control Firefox by closing the active tab."""
    try:
        # Find the first visible Firefox window
        win_id = subprocess.check_output(
            ["xdotool", "search", "--onlyvisible", "--class", "Firefox"]
        ).decode().splitlines()[0]
        # Activate the window
        subprocess.run(["xdotool", "windowactivate", win_id])
        time.sleep(0.5)  # Small delay for stability
        subprocess.run(["xdotool", "key", "ctrl+w"]) # Close the current tab
        time.sleep(0.5)  # Small delay for stability
        minimize_windows()
    except IndexError:
        print("No Firefox window found to close")
    except subprocess.CalledProcessError:
        print("xdotool command failed")

def minimize_windows():
    subprocess.run(["xdotool", "key", "super+d"])  # show the desktop (minimize all windows)

def save_rotate_streamers(count_name_sets, ROTATE_STREAMER_FILE):
    with open(ROTATE_STREAMER_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Count', 'Streamer'])
        for count, streamer, _ in count_name_sets:
            writer.writerow([count, streamer])

def stage_safe_zone_check():
    clear_screen()
    if should_skip_twitch_check_and_move_mouse():
        print("Twitch Viewer processing is PAUSED.")
        time.sleep(int(SAFE_ZONE_RECHECK))
        if should_skip_twitch_check_and_move_mouse():
            return False
        else:
            clear_screen()
    return True

def stage_twitch_processing(active_firefox_streamer=None):
    token = get_access_token()
    streamers = read_streamers(STREAMER_ROTATE_FILE)
    valid_users, not_found = get_valid_users(streamers, token)
    live_streams = get_live_streams(valid_users, token)
    if live_streams:
        live_streams.sort(key=lambda x: int(x['priority']) if str(x['priority']).isdigit() else 9999)
        for s in live_streams:
            cat = f"({s['category']})" if s['category'] else "(N/A)"
            print(f"{s['priority']} - {s['name']} - {s['game']} - {cat}")
        write_live_streamers_csv(ACTIVE_STREAMER_FILE, live_streams)
        compare_rotate_streamers(live_streams)
    else:
        print("No streamers live.")
        write_live_streamers_csv(ACTIVE_STREAMER_FILE, [])
        compare_rotate_streamers([])

    if not_found:
        print("\nUsers not found on Twitch:")
        for name in not_found:
            print(f"- {name}")
        write_missing_streamers_file(MISSING_STREAMER_FILE, not_found)

    return live_streams

def write_missing_streamers_file(filename, missing_streamers):
    with open(filename, 'w', encoding='utf-8') as f:
        for streamer in missing_streamers:
            f.write(streamer + '\n')

if __name__ == "__main__":
    if stage_safe_zone_check():
        firefox_data = check_firefox_streamer()
        active_firefox_streamer = firefox_data.get("streamer")
        stage_twitch_processing(active_firefox_streamer)
