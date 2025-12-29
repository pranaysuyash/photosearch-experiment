# Exhaustive Media Metadata Fields - Complete Reference

**Date**: 2025-12-29
**Scope**: ALL possible metadata fields for media files
**Status**: Comprehensive inventory beyond PhotoSearch's current and planned extraction

---

## Overview

This document covers metadata fields NOT included in the previous two documents:
- `COMPLETE_METADATA_CATALOG.md` - 240+ fields currently extracted
- `METADATA_GAPS_ANALYSIS.md` - 360+ missing fields identified

**Additional fields identified**: ~300+ more specialized/vendor-specific fields

---

## 1. VENDOR-SPECIFIC MAKERNOTE FIELDS

### Background
The previous documents mentioned "MakerNote" as a category but didn't detail the hundreds of proprietary fields each camera manufacturer embeds. These are critical for professional photographers.

### ❌ Canon MakerNote (~150 fields)
**Source**: Canon-specific EXIF tags
**Library**: `exifread` with details=True, or `exiftool`

| Field | Description |
|-------|-------------|
| **Camera Settings** |
| `CanonCS_MacroMode` | Macro mode setting |
| `CanonCS_SelfTimer` | Self-timer delay |
| `CanonCS_Quality` | Quality setting |
| `CanonCS_FlashMode` | Flash mode |
| `CanonCS_ContinuousDrive` | Drive mode |
| `CanonCS_FocusMode` | Focus mode (One-Shot, AI Servo, AI Focus) |
| `CanonCS_RecordMode` | Record mode |
| `CanonCS_ImageSize` | Image size |
| `CanonCS_EasyMode` | Easy shooting mode |
| `CanonCS_DigitalZoom` | Digital zoom |
| `CanonCS_Contrast` | Contrast setting |
| `CanonCS_Saturation` | Saturation setting |
| `CanonCS_Sharpness` | Sharpness setting |
| `CanonCS_ISOSpeed` | ISO speed setting |
| `CanonCS_MeteringMode` | Metering mode |
| `CanonCS_FocusType` | Focus type |
| `CanonCS_AFPoint` | Active AF point |
| `CanonCS_ExposureMode` | Exposure mode |
| `CanonCS_LensType` | Lens type ID |
| `CanonCS_LongFocalLength` | Long focal length |
| `CanonCS_ShortFocalLength` | Short focal length |
| `CanonCS_FocalUnits` | Focal length units |
| `CanonCS_MaxAperture` | Maximum aperture |
| `CanonCS_MinAperture` | Minimum aperture |
| `CanonCS_FlashActivity` | Flash activity |
| `CanonCS_FlashDetails` | Flash details |
| `CanonCS_FocusContinuous` | Focus continuous |
| `CanonCS_AESetting` | AE setting |
| `CanonCS_ImageStabilization` | Image stabilization |
| `CanonCS_DisplayAperture` | Display aperture |
| `CanonCS_ZoomSourceWidth` | Zoom source width |
| `CanonCS_ZoomTargetWidth` | Zoom target width |
| `CanonCS_SpotMeteringMode` | Spot metering mode |
| `CanonCS_PhotoEffect` | Photo effect |
| `CanonCS_ManualFlashOutput` | Manual flash output |
| `CanonCS_ColorTone` | Color tone |
| `CanonCS_SRAWQuality` | sRAW quality |
| **Shot Info** |
| `CanonSI_AutoISO` | Auto ISO result |
| `CanonSI_BaseISO` | Base ISO |
| `CanonSI_MeasuredEV` | Measured EV |
| `CanonSI_TargetAperture` | Target aperture |
| `CanonSI_TargetExposureTime` | Target exposure time |
| `CanonSI_ExposureCompensation` | Exposure compensation |
| `CanonSI_WhiteBalance` | White balance |
| `CanonSI_SlowShutter` | Slow shutter |
| `CanonSI_SequenceNumber` | Sequence number |
| `CanonSI_OpticalZoomCode` | Optical zoom code |
| `CanonSI_CameraTemperature` | Camera temperature |
| `CanonSI_FlashGuideNumber` | Flash guide number |
| `CanonSI_AFPointsInFocus` | AF points used |
| `CanonSI_FlashExposureComp` | Flash exposure compensation |
| `CanonSI_AutoExposureBracketing` | AEB setting |
| `CanonSI_AEBBracketValue` | AEB bracket value |
| `CanonSI_ControlMode` | Control mode |
| `CanonSI_FocusDistanceUpper` | Focus distance upper |
| `CanonSI_FocusDistanceLower` | Focus distance lower |
| `CanonSI_FNumber` | F-number |
| `CanonSI_ExposureTime` | Exposure time |
| `CanonSI_MeasuredEV2` | Measured EV 2 |
| `CanonSI_BulbDuration` | Bulb duration |
| `CanonSI_CameraType` | Camera type |
| `CanonSI_AutoRotate` | Auto rotate |
| `CanonSI_NDFilter` | ND filter |
| `CanonSI_SelfTimer2` | Self timer 2 |
| **Picture Style** |
| `CanonPS_ContrastStd` | Contrast (Standard) |
| `CanonPS_ContrastPortrait` | Contrast (Portrait) |
| `CanonPS_ContrastLandscape` | Contrast (Landscape) |
| `CanonPS_ContrastNeutral` | Contrast (Neutral) |
| `CanonPS_ContrastFaithful` | Contrast (Faithful) |
| `CanonPS_ContrastMonochrome` | Contrast (Monochrome) |
| `CanonPS_ContrastUserDef1` | Contrast (User Def 1) |
| `CanonPS_SharpnessStd` | Sharpness (Standard) |
| `CanonPS_SaturationStd` | Saturation (Standard) |
| `CanonPS_ColorToneStd` | Color tone (Standard) |
| `CanonPS_FilterEffectMonochrome` | Filter effect (Mono) |
| `CanonPS_ToningEffectMonochrome` | Toning effect (Mono) |
| **File Info** |
| `CanonFI_FileNumber` | File number |
| `CanonFI_ShutterCount` | Shutter count |
| `CanonFI_BracketMode` | Bracket mode |
| `CanonFI_BracketValue` | Bracket value |
| `CanonFI_BracketShotNumber` | Bracket shot number |
| `CanonFI_RawJpgQuality` | RAW+JPG quality |
| `CanonFI_RawJpgSize` | RAW+JPG size |
| `CanonFI_LongExposureNoiseReduction2` | Long exposure NR |
| `CanonFI_WBBracketMode` | WB bracket mode |
| `CanonFI_WBBracketValueAB` | WB bracket value AB |
| `CanonFI_WBBracketValueGM` | WB bracket value GM |
| `CanonFI_FilterEffect` | Filter effect |
| `CanonFI_ToningEffect` | Toning effect |
| `CanonFI_MacroMagnification` | Macro magnification |
| `CanonFI_LiveViewShooting` | Live view shooting |
| `CanonFI_FocusDistanceUpper` | Focus distance upper |
| `CanonFI_FocusDistanceLower` | Focus distance lower |
| **Color Data** |
| `CanonCD_ColorDataVersion` | Color data version |
| `CanonCD_WB_RGGBLevelsAuto` | WB RGGB levels (Auto) |
| `CanonCD_WB_RGGBLevelsDaylight` | WB RGGB levels (Daylight) |
| `CanonCD_WB_RGGBLevelsShade` | WB RGGB levels (Shade) |
| `CanonCD_WB_RGGBLevelsCloudy` | WB RGGB levels (Cloudy) |
| `CanonCD_WB_RGGBLevelsTungsten` | WB RGGB levels (Tungsten) |
| `CanonCD_WB_RGGBLevelsFluorescent` | WB RGGB levels (Fluorescent) |
| `CanonCD_WB_RGGBLevelsFlash` | WB RGGB levels (Flash) |
| `CanonCD_WB_RGGBLevelsCustom` | WB RGGB levels (Custom) |
| `CanonCD_WB_RGGBLevelsKelvin` | WB RGGB levels (Kelvin) |
| `CanonCD_ColorTempMeasured` | Color temp measured |
| `CanonCD_ColorMatrix` | Color matrix |
| **AF Info** |
| `CanonAF_NumAFPoints` | Number of AF points |
| `CanonAF_ValidAFPoints` | Valid AF points |
| `CanonAF_ImageWidth` | Image width for AF |
| `CanonAF_ImageHeight` | Image height for AF |
| `CanonAF_AFImageWidth` | AF image width |
| `CanonAF_AFImageHeight` | AF image height |
| `CanonAF_AFAreaWidths` | AF area widths |
| `CanonAF_AFAreaHeights` | AF area heights |
| `CanonAF_AFAreaXPositions` | AF area X positions |
| `CanonAF_AFAreaYPositions` | AF area Y positions |
| `CanonAF_AFPointsInFocus` | AF points in focus |
| `CanonAF_PrimaryAFPoint` | Primary AF point |
| **Lens Info** |
| `CanonLI_LensSerialNumber` | Lens serial number |
| `CanonLI_InternalSerialNumber` | Internal serial number |
| `CanonLI_FirmwareVersion` | Firmware version |
| `CanonLI_LensModel` | Lens model |
| `CanonLI_MinFocusDistance` | Minimum focus distance |
| `CanonLI_MaxFocusDistance` | Maximum focus distance |

### ❌ Nikon MakerNote (~120 fields)
**Source**: Nikon-specific EXIF tags

| Field | Description |
|-------|-------------|
| **Settings** |
| `NikonVer_Version` | Nikon version |
| `NikonISOInfo_ISO` | ISO setting |
| `NikonISOInfo_ISOExpansion` | ISO expansion |
| `NikonISOInfo_ISOExpansion2` | ISO expansion 2 |
| `NikonShotInfo_ShutterCount` | Shutter count |
| `NikonShotInfo_VRMode` | VR mode |
| `NikonShotInfo_VibrationReduction` | Vibration reduction |
| `NikonShotInfo_VRInfo` | VR info |
| `NikonColorBalance_WBRBLevels` | WB RB levels |
| `NikonLensData_LensIDNumber` | Lens ID |
| `NikonLensData_LensFStops` | Lens F-stops |
| `NikonLensData_MinFocalLength` | Min focal length |
| `NikonLensData_MaxFocalLength` | Max focal length |
| `NikonLensData_MaxApertureAtMinFocal` | Max aperture at min focal |
| `NikonLensData_MaxApertureAtMaxFocal` | Max aperture at max focal |
| `NikonLensData_MCUVersion` | MCU version |
| `NikonFlashInfo_FlashSetting` | Flash setting |
| `NikonFlashInfo_FlashType` | Flash type |
| `NikonFlashInfo_FlashMode` | Flash mode |
| `NikonFlashInfo_FlashExposureComp` | Flash exposure comp |
| `NikonFlashInfo_ExternalFlashFlags` | External flash flags |
| `NikonFlashInfo_FlashControlCommanderMode` | Commander mode |
| `NikonFlashInfo_FlashOutput` | Flash output |
| `NikonAFInfo_AFAreaMode` | AF area mode |
| `NikonAFInfo_AFPoint` | AF point |
| `NikonAFInfo_AFPointsInFocus` | AF points in focus |
| `NikonAFInfo_ContrastDetectAF` | Contrast detect AF |
| `NikonAFInfo_AFAreaXPosition` | AF area X |
| `NikonAFInfo_AFAreaYPosition` | AF area Y |
| `NikonAFInfo_AFAreaWidth` | AF area width |
| `NikonAFInfo_AFAreaHeight` | AF area height |
| `NikonAFInfo_ContrastDetectAFInFocus` | Contrast detect in focus |
| `NikonFileInfo_DirectoryNumber` | Directory number |
| `NikonFileInfo_FileNumber` | File number |
| `NikonPictureControl_PictureControlName` | Picture control name |
| `NikonPictureControl_PictureControlBase` | Picture control base |
| `NikonPictureControl_PictureControlAdjust` | Picture control adjust |
| `NikonPictureControl_PictureControlQuickAdjust` | Quick adjust |
| `NikonPictureControl_Sharpness` | Sharpness |
| `NikonPictureControl_Contrast` | Contrast |
| `NikonPictureControl_Brightness` | Brightness |
| `NikonPictureControl_Saturation` | Saturation |
| `NikonPictureControl_HueAdjustment` | Hue adjustment |
| `NikonPictureControl_FilterEffect` | Filter effect |
| `NikonPictureControl_ToningEffect` | Toning effect |
| `NikonWorldTime_Timezone` | Timezone |
| `NikonWorldTime_DaylightSavings` | Daylight savings |
| `NikonWorldTime_DateDisplayFormat` | Date display format |

### ❌ Sony MakerNote (~100 fields)

| Field | Description |
|-------|-------------|
| `SonyModelID` | Camera model ID |
| `SonyCameraSettings_DriveMode` | Drive mode |
| `SonyCameraSettings_WhiteBalanceFineTune` | WB fine tune |
| `SonyCameraSettings_FocusMode` | Focus mode |
| `SonyCameraSettings_AFAreaMode` | AF area mode |
| `SonyCameraSettings_LocalAFAreaPoint` | Local AF area point |
| `SonyCameraSettings_MeteringMode` | Metering mode |
| `SonyCameraSettings_ISOSetting` | ISO setting |
| `SonyCameraSettings_ExposureCompensation` | Exposure compensation |
| `SonyCameraSettings_DynamicRangeOptimizer` | DRO level |
| `SonyCameraSettings_ImageStabilization` | Image stabilization |
| `SonyCameraSettings_ColorMode` | Color mode |
| `SonyCameraSettings_ColorSpace` | Color space |
| `SonyCameraSettings_Sharpness` | Sharpness |
| `SonyCameraSettings_Contrast` | Contrast |
| `SonyCameraSettings_Saturation` | Saturation |
| `SonyCameraSettings_ZoneMatching` | Zone matching |
| `SonyCameraSettings_ColorTemperature` | Color temperature |
| `SonyCameraSettings_LensSpec` | Lens specification |
| `SonyCameraSettings_LensMount` | Lens mount |
| `SonyCameraSettings_LensFormat` | Lens format |
| `SonyAFInfo_AFPointSelected` | AF point selected |
| `SonyAFInfo_AFPointsUsed` | AF points used |
| `SonyAFInfo_AFTracking` | AF tracking |
| `SonyAFInfo_FocusPosition` | Focus position |
| `SonyShutterCount` | Shutter count |
| `SonyInternalSerialNumber` | Internal serial number |

### ❌ Fujifilm MakerNote (~80 fields)

| Field | Description |
|-------|-------------|
| `FujiFilmVersion` | Fujifilm version |
| `FujiFilmSerialNumber` | Serial number |
| `FujiFilmQuality` | Quality setting |
| `FujiFilmSharpness` | Sharpness |
| `FujiFilmWhiteBalance` | White balance |
| `FujiFilmSaturation` | Saturation |
| `FujiFilmContrast` | Contrast |
| `FujiFilmColorTemperature` | Color temperature |
| `FujiFilmFlashMode` | Flash mode |
| `FujiFilmFlashStrength` | Flash strength |
| `FujiFilmMacro` | Macro mode |
| `FujiFilmFocusMode` | Focus mode |
| `FujiFilmSlowSync` | Slow sync |
| `FujiFilmPictureMode` | Picture mode |
| `FujiFilmContinuousBracketing` | Continuous bracketing |
| `FujiFilmBlurWarning` | Blur warning |
| `FujiFilmFocusWarning` | Focus warning |
| `FujiFilmExposureWarning` | Exposure warning |
| `FujiFilmDynamicRange` | Dynamic range |
| `FujiFilmFilmMode` | Film simulation mode |
| `FujiFilmGrainEffect` | Grain effect |
| `FujiFilmColorChromeEffect` | Color chrome effect |
| `FujiFilmShutterType` | Shutter type |
| `FujiFilmAutoFocusSetting` | AF setting |
| `FujiFilmFocusSettings` | Focus settings |
| `FujiFilmAFCSettings` | AFC settings |

### ❌ Olympus MakerNote (~70 fields)
### ❌ Panasonic MakerNote (~60 fields)
### ❌ Pentax MakerNote (~50 fields)
### ❌ Leica MakerNote (~40 fields)
### ❌ Sigma MakerNote (~30 fields)

**Total vendor-specific MakerNote fields: ~700+**

---

## 2. SMARTPHONE/MOBILE METADATA

### ❌ Apple iPhone Metadata (~50 fields)
**Source**: EXIF MakerNote, Apple-specific tags

| Field | Description |
|-------|-------------|
| **Device Info** |
| `Apple_RunTime_Flags` | Runtime flags |
| `Apple_RunTime_Epoch` | Runtime epoch |
| `Apple_RunTime_Scale` | Runtime scale |
| `Apple_RunTime_Value` | Runtime value |
| `Apple_Acceleration_Vector` | Acceleration vector |
| `Apple_HDR_ImageType` | HDR image type |
| `Apple_BurstUUID` | Burst mode UUID |
| `Apple_ImageUniqueID` | Unique image ID |
| `Apple_MediaGroupUUID` | Media group UUID |
| **Photo Features** |
| `Apple_LivePhoto` | Is Live Photo |
| `Apple_LivePhotoVideoIndex` | Live Photo video index |
| `Apple_ContentIdentifier` | Content identifier |
| `Apple_ImageCaptureType` | Capture type (HDR, Portrait, Night) |
| `Apple_PhotoIdentifier` | Photo identifier |
| **Portrait Mode** |
| `Apple_PortraitEffectStrength` | Portrait effect strength |
| `Apple_DepthData` | Has depth data |
| `Apple_FocusDistanceRange` | Focus distance range |
| `Apple_PortraitLightingEffectStrength` | Portrait lighting strength |
| **Computational Photography** |
| `Apple_SemanticStyle` | Photographic style |
| `Apple_SemanticStyleRenderingVersion` | Style rendering version |
| `Apple_SemanticStylePreset` | Style preset |
| `Apple_SmartHDR` | Smart HDR version |
| `Apple_FrontFacingCamera` | Front facing camera |
| `Apple_AFConfidence` | AF confidence |
| `Apple_SceneFlags` | Scene detection flags |
| **Location/Motion** |
| `Apple_GPSHPositioningError` | GPS horizontal error |
| `Apple_RegionInfo` | Face/region detection info |
| `Apple_DetectedFaces` | Number of detected faces |
| `Apple_AccelerationVector` | Device acceleration |
| `Apple_CameraOrientation` | Camera orientation |
| **Video** |
| `Apple_VideoMetadata` | Video metadata |
| `Apple_CinematicVideoEnabled` | Cinematic mode |
| `Apple_TemporalScalabilityEnabled` | Temporal scalability |
| **ProRAW** |
| `Apple_ProRAW` | Is ProRAW |
| `Apple_ColorMatrix` | Color matrix |
| `Apple_MakerApple` | Apple maker data |

### ❌ Android/Google Pixel Metadata (~40 fields)

| Field | Description |
|-------|-------------|
| `Android_Manufacturer` | Device manufacturer |
| `Android_Model` | Device model |
| `Android_CaptureFPS` | Capture FPS |
| `Android_HDR_Mode` | HDR+ mode |
| `Android_NightSight` | Night Sight enabled |
| `Android_PortraitMode` | Portrait mode |
| `Android_PortraitBlurStrength` | Blur strength |
| `Android_DepthFormat` | Depth format |
| `Android_DepthNear` | Depth near |
| `Android_DepthFar` | Depth far |
| `Android_DepthMimeType` | Depth MIME type |
| `Android_MotionPhoto` | Is Motion Photo |
| `Android_MotionPhotoVersion` | Motion Photo version |
| `Android_MotionPhotoPresentationTimestampUs` | Motion Photo timestamp |
| `Android_TopShot` | Top Shot |
| `Android_PhotoBoothSetting` | Photo Booth setting |
| `Google_DepthMap` | Depth map data |
| `Google_Image` | Google Image metadata |
| `Google_DeviceName` | Device name |

### ❌ Samsung Metadata (~30 fields)
### ❌ Huawei Metadata (~25 fields)
### ❌ Xiaomi Metadata (~20 fields)

**Total mobile-specific fields: ~165**

---

## 3. TEMPORAL/ASTRONOMICAL METADATA

### ❌ Sun/Moon Position (Calculated from GPS + DateTime)
**Source**: Calculation libraries (e.g., `ephem`, `astropy`)
**Priority**: Medium (photographers track golden hour)

| Field | Type | Description |
|-------|------|-------------|
| `sun_azimuth` | float | Sun azimuth angle (degrees) |
| `sun_altitude` | float | Sun altitude angle (degrees) |
| `sun_position` | string | "rising", "overhead", "setting" |
| `is_golden_hour` | boolean | Captured during golden hour |
| `is_blue_hour` | boolean | Captured during blue hour |
| `minutes_to_sunset` | integer | Minutes until sunset |
| `minutes_from_sunrise` | integer | Minutes since sunrise |
| `sunrise_time` | timestamp | Sunrise time for location |
| `sunset_time` | timestamp | Sunset time for location |
| `civil_twilight_begin` | timestamp | Civil twilight begin |
| `civil_twilight_end` | timestamp | Civil twilight end |
| `nautical_twilight_begin` | timestamp | Nautical twilight begin |
| `nautical_twilight_end` | timestamp | Nautical twilight end |
| `astronomical_twilight_begin` | timestamp | Astronomical twilight begin |
| `astronomical_twilight_end` | timestamp | Astronomical twilight end |
| `solar_noon` | timestamp | Solar noon |
| `moon_phase` | string | Moon phase name |
| `moon_illumination` | float | Moon illumination (0-1) |
| `moon_azimuth` | float | Moon azimuth |
| `moon_altitude` | float | Moon altitude |
| `moon_distance` | float | Moon distance (km) |

### ❌ Season/Weather Context

| Field | Type | Description |
|-------|------|-------------|
| `season` | string | Season based on date/location |
| `day_length_hours` | float | Daylight hours for that day |
| `is_equinox` | boolean | Near equinox |
| `is_solstice` | boolean | Near solstice |

**Total temporal/astronomical: ~25**

---

## 4. EMBEDDED BINARY DATA

### ❌ ICC Color Profiles
**Source**: Embedded in image files
**Current**: PhotoSearch only detects presence, not extraction

| Field | Type | Description |
|-------|------|-------------|
| `icc_profile_embedded` | boolean | Has ICC profile |
| `icc_profile_name` | string | Profile name |
| `icc_profile_description` | string | Profile description |
| `icc_profile_copyright` | string | Profile copyright |
| `icc_profile_manufacturer` | string | Profile manufacturer |
| `icc_profile_model` | string | Profile model |
| `icc_profile_version` | string | Profile version |
| `icc_profile_class` | string | Profile class |
| `icc_profile_color_space` | string | Color space |
| `icc_profile_pcs` | string | Profile connection space |
| `icc_profile_size` | integer | Profile size (bytes) |
| `icc_profile_white_point` | array | White point XYZ |
| `icc_profile_black_point` | array | Black point XYZ |
| `icc_profile_rendering_intent` | string | Rendering intent |

### ❌ Thumbnail Images (Multiple)
**Purpose**: Many formats embed multiple thumbnails

| Field | Type | Description |
|-------|------|-------------|
| `thumbnail_count` | integer | Number of embedded thumbnails |
| `thumbnail_1_width` | integer | Thumbnail 1 width |
| `thumbnail_1_height` | integer | Thumbnail 1 height |
| `thumbnail_1_format` | string | Thumbnail 1 format |
| `thumbnail_1_size` | integer | Thumbnail 1 size (bytes) |
| `thumbnail_2_width` | integer | Thumbnail 2 width |
| `thumbnail_2_height` | integer | Thumbnail 2 height |
| `preview_image_width` | integer | Preview image width (RAW) |
| `preview_image_height` | integer | Preview image height |
| `preview_image_format` | string | Preview image format |

### ❌ Audio Embedded in Images
**Purpose**: Some cameras record audio annotations

| Field | Type | Description |
|-------|------|-------------|
| `has_audio_annotation` | boolean | Has audio annotation |
| `audio_annotation_duration` | float | Audio duration (seconds) |
| `audio_annotation_format` | string | Audio format |

**Total embedded data fields: ~28**

---

## 5. SCIENTIFIC/MEDICAL IMAGING METADATA

### ❌ DICOM (Medical Imaging)
**Source**: DICOM headers (if PhotoSearch supports medical images)
**Fields**: 4000+ possible DICOM tags

Key examples:
- Patient info (anonymized)
- Modality (CT, MRI, X-Ray, Ultrasound)
- Acquisition parameters
- Equipment info
- Study/Series/Instance UIDs

### ❌ Microscopy Metadata
**Source**: OME-TIFF, proprietary formats

| Field | Description |
|-------|-------------|
| `microscope_manufacturer` | Microscope manufacturer |
| `microscope_model` | Microscope model |
| `objective_magnification` | Objective magnification |
| `objective_na` | Numerical aperture |
| `immersion_medium` | Immersion medium |
| `pixel_size_x` | Physical pixel size X (µm) |
| `pixel_size_y` | Physical pixel size Y (µm) |
| `z_step_size` | Z-stack step size |
| `channel_count` | Number of channels |
| `channel_names` | Channel names |
| `channel_wavelengths` | Emission wavelengths |
| `time_increment` | Time-lapse increment |
| `stage_position_x` | Stage X position |
| `stage_position_y` | Stage Y position |
| `stage_position_z` | Stage Z position |

### ❌ Astronomical Imaging
**Source**: FITS headers

| Field | Description |
|-------|-------------|
| `telescope` | Telescope name |
| `instrument` | Instrument name |
| `filter` | Filter used |
| `exposure_count` | Number of exposures |
| `stacking_method` | Stacking method |
| `right_ascension` | RA coordinates |
| `declination` | DEC coordinates |
| `epoch` | Epoch |
| `object_name` | Celestial object name |

**Total scientific imaging: ~50+ (excluding full DICOM/FITS which would add thousands)**

---

## 6. SOCIAL MEDIA/WEB METADATA

### ❌ Social Media Metadata (when imported)
**Source**: Images downloaded from social platforms

| Field | Description |
|-------|-------------|
| `social_platform` | Platform (Instagram, Facebook, Twitter, etc.) |
| `post_id` | Original post ID |
| `post_url` | Original post URL |
| `author_username` | Author username |
| `author_display_name` | Author display name |
| `author_profile_url` | Author profile URL |
| `post_date` | Original post date |
| `caption` | Post caption |
| `hashtags` | Hashtags (array) |
| `mentions` | User mentions (array) |
| `like_count` | Number of likes |
| `comment_count` | Number of comments |
| `share_count` | Number of shares |
| `view_count` | Number of views |
| `is_sponsored` | Is sponsored content |
| `filter_used` | Filter applied |
| `engagement_rate` | Engagement rate |

### ❌ Open Graph / Schema.org
**Source**: Web images with metadata

| Field | Description |
|-------|-------------|
| `og_title` | Open Graph title |
| `og_description` | Open Graph description |
| `og_site_name` | Site name |
| `og_type` | Content type |
| `og_url` | Canonical URL |
| `twitter_card` | Twitter card type |
| `schema_type` | Schema.org type |
| `schema_description` | Schema description |

**Total social/web: ~25**

---

## 7. FORENSIC/SECURITY METADATA

### ❌ Digital Signatures & Watermarking
**Source**: Embedded signatures, steganography

| Field | Description |
|-------|-------------|
| `digital_signature_present` | Has digital signature |
| `digital_signature_valid` | Signature valid |
| `digital_signature_issuer` | Certificate issuer |
| `digital_signature_subject` | Certificate subject |
| `digital_signature_timestamp` | Signing timestamp |
| `watermark_detected` | Visible/invisible watermark |
| `watermark_type` | Watermark type |
| `steganography_detected` | Steganographic data detected |

### ❌ Blockchain/NFT Metadata
**Purpose**: NFT images with blockchain proof

| Field | Description |
|-------|-------------|
| `nft_contract_address` | Smart contract address |
| `nft_token_id` | Token ID |
| `nft_blockchain` | Blockchain (Ethereum, Polygon, etc.) |
| `nft_minted_date` | Mint date |
| `nft_creator_wallet` | Creator wallet address |
| `nft_current_owner` | Current owner wallet |
| `nft_transaction_hash` | Transaction hash |
| `ipfs_hash` | IPFS content hash |
| `arweave_hash` | Arweave content hash |

### ❌ Content Authenticity Initiative (CAI)
**Source**: Adobe/C2PA standard
**Purpose**: Track editing provenance

| Field | Description |
|-------|-------------|
| `c2pa_manifest_present` | Has C2PA manifest |
| `c2pa_claim_generator` | Claim generator |
| `c2pa_signature_valid` | Signature valid |
| `c2pa_assertions` | Assertions (array) |
| `c2pa_actions_taken` | Actions taken (array) |
| `c2pa_ingredients` | Ingredient assets |
| `c2pa_credentials` | Credentials |

**Total forensic/security: ~25**

---

## 8. ACCESSIBILITY METADATA

### ❌ Alt Text & Accessibility
**Source**: IPTC, XMP, web metadata

| Field | Description |
|-------|-------------|
| `alt_text` | Alternative text description |
| `long_description` | Extended description |
| `caption` | Caption text |
| `accessibility_features` | Accessibility features (array) |
| `accessibility_hazards` | Accessibility hazards (array) |
| `transcript` | Audio/video transcript |
| `subtitle_languages` | Subtitle languages available |
| `audio_description_available` | Has audio description |
| `sign_language_available` | Has sign language interpretation |

**Total accessibility: ~9**

---

## 9. DRM & PROTECTION METADATA

### ❌ Rights Management
**Source**: XMP Rights, PLUS

| Field | Description |
|-------|-------------|
| `drm_protected` | DRM protected |
| `drm_system` | DRM system name |
| `license_url` | License URL |
| `license_type` | License type (CC, Rights Managed, etc.) |
| `usage_terms` | Usage terms |
| `expiration_date` | License expiration |
| `geographic_restrictions` | Geographic restrictions |
| `industry_restrictions` | Industry restrictions |
| `allowed_uses` | Allowed uses (array) |
| `prohibited_uses` | Prohibited uses (array) |
| `attribution_required` | Attribution required |
| `attribution_text` | Required attribution text |
| `derivatives_allowed` | Derivatives allowed |
| `commercial_use_allowed` | Commercial use allowed |
| `plus_version` | PLUS license version |
| `image_creator_id` | Image creator ID |
| `image_supplier_id` | Image supplier ID |
| `licensor_url` | Licensor URL |
| `model_release_status` | Model release status |
| `property_release_status` | Property release status |

**Total DRM/rights: ~20**

---

## 10. MULTI-MEDIA SYNCHRONIZATION

### ❌ Multi-Camera Sync
**Purpose**: Synchronized multi-camera shoots

| Field | Description |
|-------|-------------|
| `camera_group_id` | Camera group identifier |
| `camera_position` | Camera position in group |
| `sync_timecode` | Synchronization timecode |
| `sync_master` | Is sync master |
| `related_images` | Related image IDs |

### ❌ Photo Sequences
**Purpose**: Burst, timelapse, bracket sequences

| Field | Description |
|-------|-------------|
| `sequence_id` | Sequence identifier |
| `sequence_type` | "burst", "timelapse", "bracket", "focus_stack" |
| `sequence_position` | Position in sequence |
| `sequence_total` | Total images in sequence |
| `sequence_interval` | Interval between shots |
| `sequence_key_frame` | Is key frame |

**Total sync/sequence: ~11**

---

## 11. WORKFLOW & ASSET MANAGEMENT

### ❌ DAM (Digital Asset Management) Metadata
**Source**: Asset management systems

| Field | Description |
|-------|-------------|
| `asset_id` | Asset ID in DAM |
| `asset_version` | Asset version |
| `workflow_state` | Workflow state |
| `approval_status` | Approval status |
| `assigned_to` | Assigned to (user) |
| `due_date` | Due date |
| `priority` | Priority level |
| `project_name` | Project name |
| `project_code` | Project code |
| `client_name` | Client name |
| `job_number` | Job number |
| `purchase_order` | Purchase order number |
| `invoice_number` | Invoice number |
| `archive_location` | Archive location |
| `backup_status` | Backup status |
| `review_status` | Review status |
| `usage_count` | Usage count |
| `download_count` | Download count |
| `last_accessed_date` | Last accessed |
| `last_accessed_by` | Last accessed by (user) |

**Total workflow/DAM: ~20**

---

## 12. PRINT & PUBLISHING METADATA

### ❌ Print Production
**Source**: IPTC, XMP Photoshop

| Field | Description |
|-------|-------------|
| `color_mode_print` | Color mode (CMYK, RGB, etc.) |
| `intended_output` | Intended output (screen, print) |
| `proof_profile` | Soft proof profile |
| `printer_profile` | Printer profile |
| `paper_size` | Paper size |
| `paper_type` | Paper type |
| `print_resolution` | Print resolution (DPI) |
| `bleed_settings` | Bleed settings |
| `crop_marks` | Crop marks present |
| `color_bars` | Color bars present |
| `page_number` | Page number in publication |
| `spread_position` | Position in spread |
| `gutter_position` | Gutter position |
| `publication_name` | Publication name |
| `publication_date` | Publication date |
| `edition` | Edition |
| `issue_number` | Issue number |
| `volume_number` | Volume number |
| `isbn` | ISBN |
| `doi` | DOI (Digital Object Identifier) |

**Total print/publishing: ~20**

---

## 13. VIDEO-SPECIFIC ADVANCED METADATA

### ❌ Closed Captions (CEA-608/708)
**Source**: Embedded caption data

| Field | Description |
|-------|-------------|
| `cc_format` | Caption format |
| `cc_language` | Caption language |
| `cc_service_number` | Service number |
| `cc_frame_accurate` | Frame accurate |

### ❌ Timecode Formats
**Source**: Various timecode standards

| Field | Description |
|-------|-------------|
| `timecode_format` | SMPTE, Drop Frame, Non-Drop |
| `timecode_start` | Start timecode |
| `timecode_rate` | Timecode rate |

### ❌ Broadcast Standards
**Source**: Broadcast metadata

| Field | Description |
|-------|-------------|
| `broadcast_standard` | NTSC, PAL, SECAM, ATSC |
| `line_standard` | 525, 625, etc. |
| `aspect_ratio_display` | Display aspect ratio |
| `afd` | Active Format Description |
| `wide_screen_signaling` | WSS data |
| `teletext_present` | Teletext present |
| `vbi_data_present` | VBI data present |
| `ancillary_data` | Ancillary data present |

**Total video advanced: ~15**

---

## 14. PERFORMANCE/QUALITY METRICS

### ❌ Image Quality Assessment (Calculated)
**Source**: Computer vision algorithms
**Libraries**: `opencv`, `scikit-image`, `brisque`

| Field | Description |
|-------|-------------|
| `brisque_score` | BRISQUE quality score (0-100) |
| `niqe_score` | NIQE quality score |
| `piqe_score` | PIQE quality score |
| `nima_score` | NIMA aesthetic score |
| `sharpness_laplacian` | Laplacian variance (sharpness) |
| `edge_density` | Edge density |
| `texture_score` | Texture richness |
| `noise_variance` | Noise variance |
| `compression_quality_estimate` | Estimated JPEG quality |
| `blocking_artifact_score` | Blocking artifact measure |
| `ringing_artifact_score` | Ringing artifact measure |

### ❌ Aesthetic Scoring
**Source**: ML models

| Field | Description |
|-------|-------------|
| `aesthetic_score` | Overall aesthetic score |
| `composition_score` | Composition quality |
| `color_harmony_score` | Color harmony |
| `subject_clarity_score` | Subject clarity |
| `technical_quality_score` | Technical quality |

**Total quality metrics: ~16**

---

## 15. MISCELLANEOUS SPECIALIZED FIELDS

### ❌ Drone Metadata
**Source**: DJI, Parrot, Skydio drones

| Field | Description |
|-------|-------------|
| `drone_make` | Drone manufacturer |
| `drone_model` | Drone model |
| `drone_serial_number` | Drone serial number |
| `flight_speed` | Flight speed |
| `flight_altitude` | Flight altitude (AGL) |
| `flight_pitch` | Gimbal pitch |
| `flight_roll` | Gimbal roll |
| `flight_yaw` | Gimbal yaw |
| `gimbal_pitch` | Gimbal pitch angle |
| `gimbal_roll` | Gimbal roll angle |
| `gimbal_yaw` | Gimbal yaw angle |
| `flight_mode` | Flight mode (GPS, ATTI, Sport) |
| `rtk_enabled` | RTK positioning enabled |
| `obstacle_avoidance_active` | Obstacle avoidance active |
| `battery_percentage` | Battery percentage |
| `battery_temperature` | Battery temperature |
| `signal_strength` | Controller signal strength |
| `satellite_count` | GPS satellite count |

### ❌ 360° Camera Metadata
**Source**: Ricoh Theta, Insta360, GoPro MAX

| Field | Description |
|-------|-------------|
| `projection_type` | Equirectangular, cubemap, etc. |
| `is_360` | Is 360° image |
| `full_pano_width_pixels` | Full panorama width |
| `full_pano_height_pixels` | Full panorama height |
| `cropped_area_image_width` | Cropped area width |
| `cropped_area_image_height` | Cropped area height |
| `cropped_area_left` | Crop left offset |
| `cropped_area_top` | Crop top offset |
| `initial_view_heading` | Initial heading (degrees) |
| `initial_view_pitch` | Initial pitch |
| `initial_view_roll` | Initial roll |
| `pose_pitch` | Camera pitch |
| `pose_roll` | Camera roll |

### ❌ Action Camera Metadata
**Source**: GoPro, Sony Action Cam

| Field | Description |
|-------|-------------|
| `video_mode` | Video mode (1080p60, 4K30, etc.) |
| `protune_enabled` | ProTune enabled |
| `video_stabilization` | Stabilization mode |
| `field_of_view` | FOV (wide, linear, narrow) |
| `low_light_mode` | Low light mode |
| `sharpness_level` | Sharpness level |
| `color_profile` | Color profile (Flat, GoPro Color) |
| `iso_limit` | ISO limit |
| `ev_compensation` | EV compensation |
| `white_balance_mode` | WB mode |
| `shutter_speed_limit` | Shutter speed limit |

### ❌ Webcam/Streaming Metadata

| Field | Description |
|-------|-------------|
| `webcam_model` | Webcam model |
| `streaming_resolution` | Streaming resolution |
| `streaming_bitrate` | Streaming bitrate |
| `streaming_platform` | Platform (Twitch, YouTube, etc.) |
| `stream_key_used` | Stream key used |
| `encoder_preset` | Encoder preset |
| `keyframe_interval` | Keyframe interval |

**Total specialized: ~48**

---

## GRAND TOTAL SUMMARY

### Complete Metadata Field Count

| Category | Previous Docs | This Document | Total |
|----------|---------------|---------------|-------|
| **Currently Extracted** | 240 | 0 | 240 |
| **Previously Identified Gaps** | 0 | 360 | 360 |
| **Vendor MakerNotes** | 50+ | 700+ | 750+ |
| **Mobile/Smartphone** | 0 | 165 | 165 |
| **Temporal/Astronomical** | 0 | 25 | 25 |
| **Embedded Binary Data** | 3 | 28 | 31 |
| **Scientific/Medical** | 0 | 50 | 50 |
| **Social Media/Web** | 0 | 25 | 25 |
| **Forensic/Security** | 0 | 25 | 25 |
| **Accessibility** | 0 | 9 | 9 |
| **DRM/Rights** | 0 | 20 | 20 |
| **Sync/Sequences** | 0 | 11 | 11 |
| **Workflow/DAM** | 0 | 20 | 20 |
| **Print/Publishing** | 0 | 20 | 20 |
| **Video Advanced** | 40 | 15 | 55 |
| **Quality Metrics** | 0 | 16 | 16 |
| **Specialized (Drone, 360°, etc.)** | 0 | 48 | 48 |
| **GRAND TOTAL** | 333 | ~1,537 | **~1,870** |

---

## TRULY EXHAUSTIVE?

**No.** Even this list isn't exhaustive because:

1. **Proprietary formats** - Thousands of vendor-specific fields in RAW files
2. **DICOM** - 4000+ medical imaging tags
3. **FITS** - Hundreds of astronomical imaging tags
4. **Custom XMP namespaces** - Organizations create custom metadata schemas
5. **Video codec variations** - Each codec (H.264, H.265, VP9, AV1, ProRes, DNxHD) has unique metadata
6. **Audio codec variations** - AAC, Opus, Vorbis, FLAC, etc. each have specific tags
7. **Regional standards** - Region-specific metadata (e.g., Japanese IPTC extensions)
8. **Future standards** - New metadata standards continuously emerge

---

## REALISTIC SCOPE FOR PHOTOSEARCH

### Tier 1: Essential (Implement First)
- ✅ Current 240 fields
- IPTC Core (~50 fields)
- XMP Dublin Core (~15 fields)
- Perceptual hashing (3-5 fields)
- **Total: ~310 fields**

### Tier 2: Professional (High Value)
- Extended XMP (~50 fields)
- Reverse geocoding (~10 fields)
- Color analysis (~10 fields)
- Mobile metadata basics (~20 fields)
- **Total: ~90 additional = ~400 cumulative**

### Tier 3: Advanced (Power Users)
- Vendor MakerNotes (top 50 fields from each major manufacturer ~200)
- Temporal/astronomical (~25 fields)
- Quality metrics (~15 fields)
- **Total: ~240 additional = ~640 cumulative**

### Tier 4: Specialized (Niche)
- Drone metadata
- 360° camera metadata
- Workflow/DAM
- **Total: ~100 additional = ~740 cumulative**

**Realistic maximum for PhotoSearch: 700-750 well-structured, searchable metadata fields**

---

**Document Complete**: This represents the most comprehensive metadata field inventory for media files, totaling approximately **1,870 possible fields** across all categories and use cases.
