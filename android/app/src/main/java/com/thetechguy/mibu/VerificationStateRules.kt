package com.thetechguy.mibu

fun VerificationState.isAuthoritativeResult(): Boolean = when (this) {
    VerificationState.WAIT_TIME_SHOWN,
    VerificationState.ACCOUNT_DEVICE_NOT_ADDED,
    VerificationState.COMMUNITY_AUTH_REQUIRED,
    VerificationState.UNLOCKED -> true
    else -> false
}

fun VerificationState.isTimingComplete(): Boolean =
    this == VerificationState.TIMING_WINDOW_REACHED ||
        this == VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION

fun VerificationState.blocksNewWaitingCycle(): Boolean = isTimingComplete() || isAuthoritativeResult()
