package cc.chenx.flclash.service.models

data class NotificationParams(
    val title: String = "TENVPN",
    val onlyStatisticsProxy: Boolean = false,
    val showStopAction: Boolean = true,
    val networkSpeedNotification: Boolean = false,
)
