TOKEN_URL = 'https://id.twitch.tv/oauth2/token'
TWITCH_API_URL = 'https://api.twitch.tv/helix/streams'

STREAMER_ROTATE_FILE = "TwitchStreamers.csv"  # File containing the list of usernames to check
ACTIVE_STREAMER_FILE = "LiveStreamers.csv"  # File containing the list of active streamers
ROTATE_STREAMER_FILE = "ViewingStreamers.csv"  # File containing the list of live streamers to rotate though

SCREEN_SAFE_ZONE = "287" # zone is the right side of screen in pixels
SAFE_ZONE_RECHECK = "30" # zone recheck is how long the script waits after a safe zone detection before checking again

VIEW_LIMIT_COUNT = "3" #the number of times the script will select the same streamer, when multiple streamers are found
