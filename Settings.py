TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_API_URL = "https://api.twitch.tv/helix/streams"

STREAMER_ROTATE_FILE = "TwitchStreamers.csv"  # File containing the list of usernames to check
ACTIVE_STREAMER_FILE = "LiveStreamers.csv"  # File containing the list of active streamers
ROTATE_STREAMER_FILE = "ViewedStreamers.csv"  # File containing the list of live streamers to rotate though
MISSING_STREAMER_FILE = "MissingStreamers.txt"  # File containing the list of streamers from STREAMER_ROTATE_FILE that were unable to be found (wrong spelling/streamer changed names) 

SCREEN_SAFE_ZONE = 287 # Zone is the right side of the screen in pixels
SAFE_ZONE_RECHECK = 30 # Zone recheck is how long the script waits after a save zone detection before checking again

VIEW_LIMIT_COUNT = 3 # The number of times the script will select the same streamer, when multiple streamers are found 
