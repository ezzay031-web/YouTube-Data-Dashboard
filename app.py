import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from googleapiclient.discovery import build
from datetime import datetime
import re
from typing import Dict, List, Optional


st.set_page_config(
    page_title="YouTube Data Dashboard",
    page_icon="",
    layout="wide"
)

#  CSS
st.markdown("""
<style>
    .main-title {
        text-align: center;
        padding: 20px;
        background: linear-gradient(135deg, #ff0000, #cc0000);
        color: white;
        border-radius: 10px;
        margin-bottom: 30px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

def format_number(num):
    """Format large numbers"""
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}K"
    return str(num)

def parse_duration(duration_str):
    """Parse YouTube duration format to minutes"""
    pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
    match = pattern.match(duration_str)
    
    if not match:
        return 0
    
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    
    return hours * 60 + minutes + seconds / 60

class YouTubeAPI:
    def __init__(self, api_key):
        self.youtube = build('youtube', 'v3', developerKey=api_key)
    
    def get_channel_stats(self, channel_id):
        """Get channel statistics"""
        try:
            request = self.youtube.channels().list(
                part='snippet,statistics,contentDetails',
                id=channel_id
            )
            response = request.execute()
            
            if not response['items']:
                return None
            
            channel = response['items'][0]
            return {
                'title': channel['snippet']['title'],
                'subscribers': int(channel['statistics']['subscriberCount']),
                'views': int(channel['statistics']['viewCount']),
                'videos': int(channel['statistics']['videoCount']),
                'thumbnail': channel['snippet']['thumbnails']['high']['url'],
                'playlist_id': channel['contentDetails']['relatedPlaylists']['uploads']
            }
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return None
    
    def get_videos(self, playlist_id, max_results=50):
        """Get videos from channel"""
        video_ids = []
        next_page_token = None
        
        while len(video_ids) < max_results:
            request = self.youtube.playlistItems().list(
                part='contentDetails',
                playlistId=playlist_id,
                maxResults=min(50, max_results - len(video_ids)),
                pageToken=next_page_token
            )
            response = request.execute()
            
            for item in response['items']:
                video_ids.append(item['contentDetails']['videoId'])
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        
        # video details
        videos_data = []
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]
            request = self.youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(batch_ids)
            )
            response = request.execute()
            
            for video in response['items']:
                videos_data.append({
                    'title': video['snippet']['title'],
                    'published_at': video['snippet']['publishedAt'],
                    'views': int(video['statistics'].get('viewCount', 0)),
                    'likes': int(video['statistics'].get('likeCount', 0)),
                    'comments': int(video['statistics'].get('commentCount', 0)),
                    'duration': parse_duration(video['contentDetails']['duration'])
                })
        
        return videos_data

def main():
    # Title
    st.markdown('<div class="main-title"><h1> YouTube Data Dashboard</h1><p>Analyze video views, watch time, subscriber growth, and engagement</p></div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header(" Configuration")
        
        api_key = st.text_input(
            "YouTube API Key",
            type="password",
            help="Get your API key from Google Cloud Console"
        )
        
        channel_id = st.text_input(
            "Channel ID",
            help="Example: UCXuqSBlHAE6Xw-yeJA0Tunw"
        )
        
        st.markdown("---")
        st.header(" Settings")
        
        max_videos = st.slider(
            "Number of videos to analyze",
            min_value=10,
            max_value=100,
            value=50,
            step=10
        )
        
        st.markdown("---")
        st.markdown("###  Instructions")
        st.markdown("""
        1. Get YouTube API key from Google Cloud Console
        2. Enable YouTube Data API v3
        3. Enter channel ID
        4. Click 'Load Data'
        """)
        
        load_button = st.button(" Load Data", type="primary")
    
    # Main content
    if load_button and api_key and channel_id:
        with st.spinner("Loading YouTube data..."):
            try:
                # Initialize API
                yt = YouTubeAPI(api_key)
                
                # Get channel stats
                channel = yt.get_channel_stats(channel_id)
                
                if not channel:
                    st.error("Channel not found. Please check channel ID.")
                    return
                
                # Get videos
                videos = yt.get_videos(channel['playlist_id'], max_videos)
                
                if not videos:
                    st.warning("No videos found.")
                    return
                
                # Create DataFrame
                df = pd.DataFrame(videos)
                df['published_at'] = pd.to_datetime(df['published_at'])
                
                # Display channel info
                st.subheader(" Channel Overview")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.image(channel['thumbnail'], width=120)
                
                with col2:
                    st.metric("Channel Name", channel['title'])
                
                with col3:
                    st.metric("Total Subscribers", format_number(channel['subscribers']))
                
                with col4:
                    st.metric("Total Views", format_number(channel['views']))
                
                st.markdown("---")
                
                # Key metrics
                st.subheader(" Key Metrics")
                col1, col2, col3, col4 = st.columns(4)
                
                total_views = df['views'].sum()
                total_likes = df['likes'].sum()
                total_comments = df['comments'].sum()
                avg_views = df['views'].mean()
                
                with col1:
                    st.metric("Total Views", format_number(total_views))
                with col2:
                    st.metric("Total Likes", format_number(total_likes))
                with col3:
                    st.metric("Total Comments", format_number(total_comments))
                with col4:
                    st.metric("Avg Views/Video", format_number(avg_views))
                
                st.markdown("---")
                
                # Interactive filters
                st.subheader(" Interactive Filters")
                col1, col2 = st.columns(2)
                
                with col1:
                    date_range = st.date_input(
                        "Date Range",
                        [df['published_at'].min().date(), df['published_at'].max().date()]
                    )
                
                with col2:
                    min_views = st.slider(
                        "Minimum Views",
                        int(df['views'].min()),
                        int(df['views'].max()),
                        int(df['views'].min())
                    )
                
                # Apply filters
                filtered_df = df[
                    (df['published_at'].dt.date >= date_range[0]) &
                    (df['published_at'].dt.date <= date_range[1]) &
                    (df['views'] >= min_views)
                ]
                
                # Bar chart for top-performing videos
                st.subheader(" Top Performing Videos")
                top_n = st.selectbox("Number of videos", [5, 10, 15, 20], index=1)
                
                top_videos = filtered_df.nlargest(top_n, 'views')
                
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(
                    x=top_videos['title'][:top_n],
                    y=top_videos['views'][:top_n],
                    marker_color="#174bd8",
                    text=top_videos['views'][:top_n].apply(format_number),
                    textposition='outside',
                    name='Views'
                ))
                
                fig_bar.update_layout(
                    title=f"Top {top_n} Videos by Views",
                    xaxis_title="Video Title",
                    yaxis_title="Views",
                    xaxis_tickangle=45,
                    height=500,
                    showlegend=True
                )
                
                st.plotly_chart(fig_bar, use_container_width=True)
                
                # Line graph for subscriber trends (simulated)
                st.subheader(" Subscriber Growth Trends")
                
                # Simulate subscriber growth based on video performance
                filtered_df = filtered_df.sort_values('published_at')
                filtered_df['cumulative_views'] = filtered_df['views'].cumsum()
                filtered_df['estimated_subscribers'] = channel['subscribers'] * (filtered_df['cumulative_views'] / channel['views'])
                
                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(
                    x=filtered_df['published_at'],
                    y=filtered_df['estimated_subscribers'],
                    mode='lines+markers',
                    name='Estimated Subscribers',
                    line=dict(color='#174bd8', width=2),
                    marker=dict(size=6)
                ))
                
                fig_line.update_layout(
                    title="Subscriber Growth Over Time",
                    xaxis_title="Publication Date",
                    yaxis_title="Subscribers",
                    height=500
                )
                
                st.plotly_chart(fig_line, use_container_width=True)
                
                # Engagement metrics
                st.subheader(" Engagement Analysis")
                
                filtered_df['engagement_rate'] = ((filtered_df['likes'] + filtered_df['comments']) / filtered_df['views'] * 100).fillna(0)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_engagement = px.bar(
                        filtered_df.nlargest(10, 'engagement_rate'),
                        x='title',
                        y='engagement_rate',
                        title="Top 10 Videos by Engagement Rate",
                        labels={'title': 'Video Title', 'engagement_rate': 'Engagement Rate (%)'},
                        color='engagement_rate',
                        color_continuous_scale='Viridis'
                    )
                    fig_engagement.update_layout(xaxis_tickangle=45, height=500)
                    st.plotly_chart(fig_engagement, use_container_width=True)
                
                with col2:
                    fig_scatter = px.scatter(
                        filtered_df,
                        x='views',
                        y='engagement_rate',
                        size='likes',
                        color='duration',
                        hover_name='title',
                        title="Views vs Engagement Rate",
                        labels={'views': 'Views', 'engagement_rate': 'Engagement Rate (%)', 'duration': 'Duration (min)'}
                    )
                    fig_scatter.update_layout(height=500)
                    st.plotly_chart(fig_scatter, use_container_width=True)
                
                # Watch time analysis
                st.subheader(" Watch Time Analysis")
                
                filtered_df['watch_time_minutes'] = filtered_df['views'] * filtered_df['duration']
                filtered_df['watch_time_hours'] = filtered_df['watch_time_minutes'] / 60
                
                fig_watch_time = px.bar(
                    filtered_df.nlargest(10, 'watch_time_hours'),
                    x='title',
                    y='watch_time_hours',
                    title="Top 10 Videos by Watch Time",
                    labels={'title': 'Video Title', 'watch_time_hours': 'Watch Time (hours)'},
                    color='watch_time_hours',
                    color_continuous_scale='Reds'
                )
                fig_watch_time.update_layout(xaxis_tickangle=45, height=500)
                st.plotly_chart(fig_watch_time, use_container_width=True)
                
                # Additional metrics
                st.subheader(" Additional Metrics")
                
                # Average video duration
                avg_duration = filtered_df['duration'].mean()
                
                # Engagement rate by day of week
                filtered_df['weekday'] = filtered_df['published_at'].dt.day_name()
                weekday_engagement = filtered_df.groupby('weekday')['engagement_rate'].mean().sort_values(ascending=False)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Average Video Duration", f"{avg_duration:.1f} minutes")
                    st.metric("Total Watch Time", f"{format_number(int(filtered_df['watch_time_hours'].sum()))} hours")
                
                with col2:
                    fig_weekday = px.bar(
                        x=weekday_engagement.index,
                        y=weekday_engagement.values,
                        title="Average Engagement Rate by Day",
                        labels={'x': 'Day of Week', 'y': 'Engagement Rate (%)'},
                        color=weekday_engagement.values,
                        color_continuous_scale='Viridis'
                    )
                    fig_weekday.update_layout(height=400)
                    st.plotly_chart(fig_weekday, use_container_width=True)
                
                # Data export
                st.subheader(" Export Data")
                
                export_df = filtered_df[['title', 'published_at', 'views', 'likes', 'comments', 'duration', 'engagement_rate', 'watch_time_hours']].copy()
                export_df['published_at'] = export_df['published_at'].dt.strftime('%Y-%m-%d')
                export_df.columns = ['Title', 'Published Date', 'Views', 'Likes', 'Comments', 'Duration (min)', 'Engagement Rate (%)', 'Watch Time (hours)']
                
                csv = export_df.to_csv(index=False)
                st.download_button(
                    label="Download Data as CSV",
                    data=csv,
                    file_name=f"youtube_data_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                
                # Success message
                st.success(f" Loaded {len(filtered_df)} videos successfully!")
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.info("Please check your API key and try again.")
    
    elif load_button:
        if not api_key:
            st.warning(" Please enter your YouTube API Key")
        if not channel_id:
            st.warning(" Please enter a Channel ID")

if __name__ == "__main__":
    main()
