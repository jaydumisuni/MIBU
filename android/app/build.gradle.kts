plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.thetechguy.mibu"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.thetechguy.mibu"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0-dev"
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
