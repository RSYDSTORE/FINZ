from kivy.app import App
from kivy.utils import platform
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle

# URL WEBSITE ANDA
TARGET_URL = "https://topup-bussid-trucksid-rsyd-store.vercel.app"

# SCRIPT JEMBATAN (INJECT KE WEBSITE)
# Ieu bakal ngahubungkeun Website -> APK
JS_BRIDGE = """
javascript:(function() {
    console.log("Rosyad Bridge Active");
    // Override Notification System
    window.show_rosyad_push_notif = function(title, body) {
        // Kirim sinyal ka APK
        window.location.href = "rosyad://notif?t=" + encodeURIComponent(title) + "&b=" + encodeURIComponent(body);
    };
    // Override Service Worker Notification
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.ready.then(function(reg) {
            reg.showNotification = function(title, options) {
                var body = options.body || '';
                window.location.href = "rosyad://notif?t=" + encodeURIComponent(title) + "&b=" + encodeURIComponent(body);
            };
        });
    }
})()
"""

class RosyadWebApp(App):
    def build(self):
        self.title = "TOP UP GAME MALEO"
        self.layout = FloatLayout()
        
        # 1. BACKGROUND HIDEUNG
        with self.layout.canvas.before:
            Color(0.05, 0.05, 0.05, 1)
            Rectangle(pos=self.layout.pos, size=Window.size)

        # 2. LOADING TEXT
        self.loading = Label(
            text="MEMUAT SYSTEM...", 
            font_size='20sp', 
            bold=True,
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.layout.add_widget(self.loading)

        # 3. FOOTER (DIPAKSA NEMPEL HANDAP)
        self.footer = Label(
            text="RsydStore || All Right Reserved 2024", 
            font_size='12sp', 
            color=(0.5, 0.5, 0.5, 1),
            size_hint=(1, None), 
            height=50,
            pos_hint={'center_x': 0.5, 'y': 0}
        )
        self.layout.add_widget(self.footer)

        # 4. AKTIFKAN SECURE FLAG (ANTI SCREENSHOT)
        self.apply_security()

        # 5. MULAI WEBVIEW
        Clock.schedule_once(self.start_webview, 1.5)
        
        return self.layout

    def apply_security(self):
        if platform == 'android':
            from jnius import autoclass
            from android.runnable import run_on_ui_thread
            
            @run_on_ui_thread
            def set_flags():
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                WindowManager = autoclass('android.view.WindowManager$LayoutParams')
                # FLAG_SECURE: Layar jadi hideung mun di-screenshot/rekam
                activity.getWindow().addFlags(WindowManager.FLAG_SECURE)
            set_flags()

    def start_webview(self, dt):
        if platform == 'android':
            from jnius import autoclass, cast, PythonJavaClass, java_method
            from android.runnable import run_on_ui_thread

            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            WebView = autoclass('android.webkit.WebView')
            WebViewClient = autoclass('android.webkit.WebViewClient')
            WebChromeClient = autoclass('android.webkit.WebChromeClient')
            CookieManager = autoclass('android.webkit.CookieManager')
            
            # --- NOTIFIKASI NATIVE ---
            def show_native_notif(title, body):
                try:
                    Context = autoclass('android.content.Context')
                    NotificationManager = autoclass('android.app.NotificationManager')
                    NotificationChannel = autoclass('android.app.NotificationChannel')
                    NotificationCompat = autoclass('androidx.core.app.NotificationCompat$Builder')
                    
                    service = activity.getSystemService(Context.NOTIFICATION_SERVICE)
                    manager = cast(NotificationManager, service)
                    
                    # Create Channel
                    channel_id = "rosyad_channel"
                    chan = NotificationChannel(channel_id, "Notifikasi Transaksi", 4) # High
                    manager.createNotificationChannel(chan)
                    
                    # Show Notif
                    icon = activity.getApplicationInfo().icon
                    builder = NotificationCompat(activity, channel_id)
                    builder.setContentTitle(title)
                    builder.setContentText(body)
                    builder.setSmallIcon(icon)
                    builder.setAutoCancel(True)
                    
                    manager.notify(1, builder.build())
                except Exception as e:
                    print(f"Notif Error: {e}")

            # --- INTERCEPTOR KHUSUS NOTIFIKASI ---
            class RosyadClient(WebViewClient):
                @java_method('(Landroid/webkit/WebView;Ljava/lang/String;)Z')
                def shouldOverrideUrlLoading(self, view, url):
                    # Nangkep sinyal ti Javascript
                    if url.startswith("rosyad://notif"):
                        try:
                            from urllib.parse import parse_qs, urlparse
                            parsed = urlparse(url)
                            params = parse_qs(parsed.query)
                            t = params.get('t', ['Info'])[0]
                            b = params.get('b', ['Pesan Baru'])[0]
                            show_native_notif(t, b)
                        except: pass
                        return True
                    return False

                @java_method('(Landroid/webkit/WebView;Ljava/lang/String;)V')
                def onPageFinished(self, view, url):
                    # Suntik JS Bridge pas loading beres
                    view.loadUrl(JS_BRIDGE)
                    super(RosyadClient, self).onPageFinished(view, url)

            @run_on_ui_thread
            def create_view():
                webview = WebView(activity)
                settings = webview.getSettings()
                
                settings.setJavaScriptEnabled(True)
                settings.setDomStorageEnabled(True)
                settings.setMixedContentMode(0) # Allow HTTP image
                settings.setJavaScriptCanOpenWindowsAutomatically(True)
                
                # User Agent Mobile
                settings.setUserAgentString("Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36")
                
                # Cookie
                CookieManager.getInstance().setAcceptCookie(True)
                CookieManager.getInstance().setAcceptThirdPartyCookies(webview, True)
                
                webview.setWebViewClient(RosyadClient())
                webview.setWebChromeClient(WebChromeClient())
                
                webview.loadUrl(TARGET_URL)
                activity.setContentView(webview)
            
            create_view()

if __name__ == '__main__':
    RosyadWebApp().run()
