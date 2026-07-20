package com.thetechguy.mibu

fun VerificationState.isAuthoritativeResult(): Boolean = when (this) {
    VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION,
    VerificationState.QUOTA_LIMIT_REACHED,
    VerificationState.BLOCKED_UNTIL_DEADLINE,
    VerificationState.WAIT_TIME_SHOWN,
    VerificationState.ACCOUNT_DEVICE_NOT_ADDED,
    VerificationState.COMMUNITY_AUTH_REQUIRED,
    VerificationState.UNLOCKED -> true
    else -> false
}

fun VerificationState.isTimingComplete(): Boolean =
    this == VerificationState.READY_FOR_MI_UNLOCK_VERIFICATION

fun VerificationState.blocksNewWaitingCycle(): Boolean = isTimingComplete() || isAuthoritativeResult()
