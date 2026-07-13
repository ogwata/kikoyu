# STATUS
状態: ctranslate2/faster-whisper のCUDA13/Blackwell動作を実機検証し、デフォルトエンジンを
faster-whisperに切り替え済み（コミット 8834d38、push済み）。誤診の再発防止として、
非互換記述の書き方を定めたCLAUDE.mdを追加（コミット 270df1d、push済み）。同内容は派生の
kikoyu-ORG（Spark bare repo, commit 3fafc51）・kikoyu-Booko（Spark bare repo, commit 22f28c2）
にもpush済み。
次: kikoyu-ORG（~/dev/LLM/kikoyu-ORG、shioiri_minutes_dgx.ipynb）のfaster-whisperへの構造修正は
適用済みだが、実データ（~54分の役員会録音）での長尺RTF実測がまだ進行中で、その数値の反映・
コミット・Spark側(~/whisperx-work)への同期push/pullが未完了。kikoyu-Bookoのdocs/mp4-workflow.md
のRTF記述更新は、kikoyu-ORG側の実測完了後に着手する。Cowork側 ai-repo-dep-check のナレッジベース
更新も未着手。手順は ~/Desktop の kikoyu-ORG-ctranslate2-cuda-handoff.md /
kikoyu-Booko-ctranslate2-cuda-handoff.md / ai-repo-dep-check-kikoyu-update-handoff.md を参照。
